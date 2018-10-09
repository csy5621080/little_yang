# -*- coding: utf-8 -*-
import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ppp_perf.settings")
django.setup()
from wf_engine.models import *
import redis
from pytz import utc
import datetime
from django.db import transaction
from wf_engine.services.func import *
import flow_config
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from django.db.models.query import Q

'''
activity func 步骤对应方法:
    *   instance_created 单个实例进程推进方法。

condition func 推进条件对应方法
    *   more_than        值大于某值可以推进
    *   less_than        值小于某值可以推进
    *   equal            值等于某值可以推进
    *   exist            对象存在可以推进
    *   not_exist        对象不存在可以推进

引擎内判断可否推进的条件分为两种:
1.push_condition        既推进条件,该条件作用于单个任务,用于判断单个任务执行是否成功.
2.arrival_condition     既抵达条件,该条件作用于流程推进目的地,既下一个步骤.当下一步标注为And,则判定属于当前步骤的所有任务均执行成功才可推进;
                                                                    当下一步标注为or,则判定属于当前步骤的任务中有任一任务执行成功即可推进.

关于流程嵌套:
   当前流程嵌套方式为动作关联,既在设计流程定义时可以选择特定的动作,在该动作下直接选择被嵌套流程定义.两流程相互独立,子流程需要单独设计,并可
独立引用使用.子流程实例在嵌套关系中,为父流程的一个完整的任务,所以,在父流程中,子流程的步骤不可见.当父流程执行到子流程对应的任务时,子流程自动
发起,独立执行.当子流程执行结束,父流程获取子流程状态,再继续推进.两流程相互关联,相对独立.

关于流程重定向:
# TODO
'''


class FlowEngine(object):
    '''
        流程引擎
    '''

    class TaskStatus(object):
        '''
            任务状态
        '''
        WAITING = 0
        RUNNING = 1
        COMPLETE = 2
        REDIRECT = 3
        CEASE = 4

    class RelationType(object):
        '''
            抵达条件
        '''
        AND = 'And'
        Or = 'Or'

    @classmethod
    def is_nest(cls, instance):
        '''
            判断是否为流程嵌套步骤
        :param instance:    任务生成对象实例
        :return:            True or False
        '''
        return isinstance(instance(), Flow)

    @classmethod
    def create_tasks(cls, flow):
        '''
                  创建任务
        :param    flow:    流程实例id
        :return:  起始任务对象
        '''

        '''获取流程对应设计下的所有步骤'''
        steps = ProcessActivityConnectionDefine.objects.filter(process_define_id=flow.process_define.id)
        '''获取起始步骤'''
        first_task = None
        for step in steps:
            if not ActivityComplexConnectionDefine.objects.filter(child_id=step.id).exists():
                owner_ids = []
                '''当步骤所属设置为某级别人员所有,则生成该级别下所有人员的task'''
                if step.own_level:
                    owner_ids += [o.id for o in User.objects.filter(perf_level_id=step.own_level.id)]
                '''若该步骤设置有所属人,将所设置的所属人纳入任务生成所属人列表'''
                if step.owner:
                    owner_ids.append(step.owner.id)
                '''当任务步骤有所属人,则循环给所有所属人生成task'''
                if owner_ids:
                    first_task = None
                    for owner_id in owner_ids:
                        task = FlowTask.objects.create(flow_id=flow.id, name=step.name, step_id=step.id,
                                                       step_num=1, owner=owner_id)
                        first_task = task
                else:
                    '''当任务无所属人则直接生成无所属人task'''
                    first_task = FlowTask.objects.create(flow_id=flow.id, name=step.name, step_id=step.id, step_num=1)
        step_num = 2

        def __create_task(father_task, step_num):
            '''
                递归创建子级任务
            :param father_task: 父任务对象
            :param step_num:    任务步骤顺序
            :return:  个屁
            '''
            '''获取下一级步骤'''
            steps = [c.child for c in ActivityComplexConnectionDefine.objects.filter(father_id=father_task.step.id)]
            for step in steps:
                if not FlowTask.objects.filter(step_id=step.id, flow_id=flow.id):
                    owner_ids = []
                    '''当步骤所属设置为某级别人员所有,则生成该级别下所有人员的task'''
                    if step.own_level:
                        owner_ids += [o.id for o in User.objects.filter(perf_level_id=step.own_level.id)]
                    '''若该步骤设置有所属人,将所设置的所属人纳入任务生成所属人列表'''
                    if step.owner:
                        owner_ids.append(step.owner.id)
                    '''当任务步骤有所属人,则循环给所有所属人生成task'''
                    if owner_ids:
                        task = None
                        for owner_id in owner_ids:
                            task = FlowTask.objects.create(flow_id=flow.id, name=step.name, step_id=step.id,
                                                           step_num=step_num, owner=owner_id)
                            task = task
                    else:
                        '''当任务无所属人则直接生成无所属人task'''
                        task = FlowTask.objects.create(flow_id=flow.id, name=step.name, step_id=step.id,
                                                       step_num=step_num)
                    '''递归调用自身寻找下一级'''
                    if father_task.id != task.id:
                        __create_task(task, step_num + 1)

        '''调用递归子方法寻找下一级'''
        __create_task(first_task, step_num)
        return first_task

    @classmethod
    def get_ready_tasks(cls, flow):
        '''
            获取当前流程实例所有待执行任务
        :param flow: 流程对象
        :return:     待执行任务集合
        '''
        ready_tasks = FlowTask.objects.filter(flow_id=flow.id, status=1)
        return ready_tasks

    @classmethod
    def get_all_next_tasks(cls, flow):
        '''
            获取所有下一步执行任务
        :param flow:  流程实例对象
        :return:      任务集合
        '''
        ready_tasks = FlowEngine.get_ready_tasks(flow)
        return FlowTask.objects.filter(step_num=ready_tasks.first().step_num + 1, flow_id=flow.id)

    @classmethod
    def get_next_tasks(cls, task):
        '''
            获取制定任务的下一步任务
        :param task: 制定任务
        :return:     下一步任务集合
        '''
        return FlowTask.objects.filter(flow_id=task.flow.id, step_num=task.step_num + 1)

    @classmethod
    def push_task(cls, task_id):
        '''
            基于指定任务推进审批流
        :param task_id: 指定任务
        :return:
        '''
        with transaction.atomic():
            task = FlowTask.objects.get(id=task_id)
            flow_status = Flow.objects.get(id=task.flow.id).status
            if flow_status == 0:
                raise FlowException(u'请先开启流程!')
            elif flow_status == 2:
                raise FlowException(u'流程已完结。')
            if task.status == 0:
                raise FlowException(u'尚未到达该动作触发时机！')
            elif task.status == 2:
                raise FlowException(u'已完成动作。')
            else:
                can_push = FlowEngine._exec(task_id)
                '''获取当前任务对应的实例'''
                instance = globals().get(task.step.activity_define.instance_model).objects.get(task_id=task_id)
                task.status = 2
                task.save()
                if can_push:
                    next_tasks = can_push
                    # if next_tasks.exists():
                    for next_task in next_tasks:
                        '''获取当前任务同步骤下的所有任务,获取所有同步骤任务状态,根据步骤设置,判断是否可推进'''
                        last_tasks = FlowTask.objects.filter(flow_id=task.flow.id, step_num=task.step_num)
                        if next_task.step.arrival_condition == FlowEngine.RelationType.AND:
                            '''当推下一步抵达条件为<全部完成时可推进>,判断可否推进'''
                            can_push = True
                            for last_task in last_tasks:
                                if last_task.status != FlowEngine.TaskStatus.COMPLETE:
                                    can_push = False
                        else:
                            '''当推下一步抵达条件为有<一个完成时可推进>,判断可否推进'''
                            can_push = False
                            for last_task in last_tasks:
                                if last_task.status == FlowEngine.TaskStatus.COMPLETE:
                                    can_push = True
                        if next_task.id != task.id and can_push:
                            '''调用 定时器 定时创建任务需要创建的对象 非定时任务则延时2秒生成'''
                            TaskTimer().create_timer_task(func=FlowEngine.create_func_instance,
                                                          params=dict(task=next_task, last_task_instance=instance),
                                                          run_time=next_task.trigger_time.strftime("%Y-%m-%d %H:%M:%S")
                                                          if next_task.trigger_time else None,
                                                          task_id=next_task.id)
                    return True
                else:
                    '''推无可推,则判定流程结束'''
                    Flow.objects.filter(id=task.flow.id).update(status=2)
                    # raise Exception(u'流程已完结。')
                    return True

    @classmethod
    def _exec(cls, task_id):
        '''
            执行条件表达式，判断任务执行方向
        :param task_id:   执行任务id
        :return:
        '''
        task = FlowTask.objects.get(id=task_id)
        '''执行任务步骤指定的方法,获取该动作相关信息,如打分动作可获取所得分数'''
        result = eval(task.step.activity_define.func_name +
                      '(owner=' + str(task.step.owner.id if task.step.owner else None) +
                      ',task_id= ' + str(task_id) +
                      ')')
        if result:
            '''获取流程下一步'''
            next_tasks = FlowEngine.get_next_tasks(task)
            can_push = []
            if next_tasks.exists():
                for next_task in next_tasks:
                    '''获取本步与下一步的关联关系,获得推进条件'''
                    relation = ActivityComplexConnectionDefine.objects.get(father_id=task.step.id,
                                                                           child_id=next_task.step_id)
                    '''执行推进条件验证方法,获知是否可以推进'''
                    condition_result = eval(relation.condition.func_name + '( ' + str(result) + ',' +
                                            str(relation.condition_result)
                                            + ')')
                    if condition_result:
                        '''当任务可以推进,则将该任务纳入可推进任务列表'''
                        can_push.append(next_task)
                if next_tasks.count() > 1 and not can_push:
                    raise FlowException(u'上一步动作不符合流程要求，推进失败！')
                elif next_tasks.count() == 1 and next_tasks.first().id != task.id and not can_push:
                    raise FlowException(u'上一步动作不符合流程要求，推进失败！')
            return can_push
        else:
            raise FlowException(task.step.activity_define.name + u'动作未完成，推进失败！')

    @classmethod
    def start(cls, flow_id):
        '''
            激活工作流，创建所有任务，并激活起始任务为等待执行状态
        :param flow_id:     流程id
        :return:
        '''
        with transaction.atomic():
            flow = Flow.objects.get(id=flow_id)
            if flow.status == 0:
                flow.status = 1
                flow.save()
                first_task = FlowEngine.create_tasks(flow=flow)
                '''调用 定时器 定时创建任务需要创建的对象 非定时任务则延时2秒生成'''
                TaskTimer().create_timer_task(func=FlowEngine.create_func_instance,
                                              params=dict(task=first_task),
                                              run_time=first_task.trigger_time.strftime("%Y-%m-%d %H:%M:%S")
                                              if first_task.trigger_time else None,
                                              task_id=first_task.id)
                # FlowEngine.create_func_instance(first_task)
            else:
                if flow.status == 1:
                    raise FlowException(u'当前流程已激活!')
                elif flow.status == 2:
                    raise FlowException(u'当前流程已完结!')

    @classmethod
    def create_func_instance(cls, task, last_task_instance=None):
        '''
            创建执行事件实例，如打分，创建打分基础数据
        :param task: 任务对象
        :return:
        '''
        is_nest = False
        '''初始化实例创建字典,任务id和流程id字段'''
        c_map = dict(flow_id=task.flow_id, task_id=task.id)
        '''任务所有人字段,任务所属对象字段,和上一步关联字段对象'''
        user_key = None
        entity_key = None
        last_step_key = None
        '''获取即将要创建的实例类对象'''
        model = globals().get(task.step.activity_define.instance_model)
        for field in model._meta.fields:
            '''获取所有该类对象的外键'''
            if field.__class__.__name__ == 'ForeignKey':
                '''用户实体'''
                if field.name == 'owner':
                    user_key = field.name + '_id'
                elif field.related_model.__name__ in [entity.__name__ for entity in flow_config.FLOW_ENTITY]:
                    '''流程依赖实体'''
                    entity_key = field.name + '_id'
                    if task.flow.rely_instance and task.flow.rely_instance == field.related_model.__name__:
                        c_map[entity_key] = task.flow.rely_pk
                elif field.related_model.__name__ == last_task_instance.__class__.__name__:
                    '''流程上一步外键关联实体'''
                    last_step_key = field.name + '_id'
            if field.name == 'owner_id':
                '''特殊操作,当当前任务为流程嵌套任务,则对应的任务实例为审批流,所有者id不可用外键关联'''
                user_key = 'owner_id'
        if task.flow.entity and entity_key:
            c_map[entity_key] = task.flow.entity.id
        if task.owner and user_key:
            c_map[user_key] = task.owner
        if last_task_instance and last_step_key:
            c_map[last_step_key] = last_task_instance.id
        if FlowEngine.is_nest(model):
            '''当判定当前任务为流程嵌套任务,则获取流程设计中选定嵌套的子流程设计对象'''
            nest_define = task.step.nest_define
            if nest_define:
                c_map['process_define_id'] = nest_define.id
            else:
                raise FlowException(u'嵌套流程不存在!')
            is_nest = True
        if not globals().get(task.step.activity_define.instance_model).objects.filter(**c_map).exists():
            '''创建任务对应实例'''
            task_instance = globals().get(task.step.activity_define.instance_model).objects.create(**c_map)
            if is_nest:
                '''当判定当前任务为流程嵌套任务, 启动子流程'''
                FlowEngine.start(task_instance.id)
        task.status = 1
        task.save()
        return True

    @classmethod
    def get_flow_forecast(cls, flow_id):
        '''
            获取流程预测
        :param flow_id: 流程实例Id
        :return:        流程预测
        '''
        tasks = FlowTask.objects.filter(flow_id=flow_id).order_by('step_num')
        return [task.serialize() for task in tasks]

    @classmethod
    def get_flow_step(cls, flow_id):
        '''
            分步骤获取流程
        :param flow_id: 流程实例ID
        :return:        流程预测 以步骤排布
        '''
        tasks = FlowTask.objects.filter(flow_id=flow_id).order_by('-step_num')
        max_num = tasks.first().step_num
        step_flow = []
        '''按步骤循环分组获取流程任务'''
        for num in range(1, max_num + 1):
            step_tasks = FlowTask.objects.filter(flow_id=flow_id, step_num=num)
            step_flow.append({"step_task": [task.serialize() for task in step_tasks],
                              "arrival_condition": step_tasks.first().step.arrival_condition})
        step_count = len(step_flow)
        '''获取每一个步骤的抵达条件'''
        for index, step in enumerate(step_flow):
            if index != step_count - 1:
                if step_flow[index + 1]['arrival_condition'] == FlowEngine.RelationType.AND:
                    step['next_arrival_condition'] = '同时满足'
                else:
                    step['next_arrival_condition'] = '有一个满足'
            else:
                step['next_arrival_condition'] = '结束'
        return step_flow

    @classmethod
    def activity_pre_set(cls):
        ActivityDefineSet = []
        for act in flow_config.ACTIVITY_ENTITY:
            if not ActivityDefine.objects.filter(instance_model=act[0].__name__).exists():
                ActivityDefineSet.append(ActivityDefine(func_name=act[2],
                                                        name=act[1],
                                                        instance_model=act[0].__name__,
                                                        class_module=act[0].__module__,
                                                        pick_field=act[3]
                                                        ))
        ActivityDefine.objects.bulk_create(ActivityDefineSet)

    @classmethod
    def roll_back(cls, task_id, to_step_num=None):
        '''
            回滚
        :param task_id:
        :param to_step_num:
        :return:
        '''
        now_task = FlowTask.objects.get(id=task_id)
        if not to_step_num:
            if now_task.step_num - 1 < 1:
                raise FlowException(u'起始步骤无法回滚')
            to_step_num = now_task.step_num - 1
        if now_task.step_num >= to_step_num:
            raise FlowException(u'请往前滚,别往后滚~')
        with transaction.atomic():
            del_tasks = FlowTask.objects.filter(step_num__gt=now_task.step_num)
            copy_tasks = FlowTask.objects.filter(step_num__gte=to_step_num)
            for copy_task in copy_tasks:
                create_dict = dict(flow_id=now_task.flow.id, name=copy_task.name, owner=copy_task.owner,
                                   step=copy_task.step, step_num=copy_task.step_num + now_task.step_num - to_step_num,
                                   trigger_time=copy_task.trigger_time)
                if copy_task.step_num == to_step_num:
                    create_dict['status'] = 1
                FlowTask.objects.create(**create_dict)
            del_tasks.delete()

    @classmethod
    def launch(cls, instance, instance_pk, define_id=None):
        '''
            流程依赖对象内部启动流程
        :param instance:        流程依赖对象
        :param instance_pk:     流程依赖对象pk
        :return:
        '''
        with transaction.atomic():
            '''获取流程依赖对象'''
            instance_obj = globals().get(instance).objects.filter(id=instance_pk)
            '''获取流程依赖对象选定的流程设计实例'''
            define_id = instance_obj.first().process_define.id
            flow = Flow.objects.create(process_define_id=define_id,
                                              rely_pk=instance_pk, rely_instance=instance)
            instance_obj.update(self_flow_id=flow.id)
            '''启动流程'''
            FlowEngine.start(flow.id)
            return True

    @classmethod
    def define_copy(cls, define_id, own_entity_id):
        '''
            流程设计复制
        :param define_id:       流程设计id
        :param own_entity_id:   复制者实体Id
        :return:
        '''

        def __colation(dic):
            '''
                字段过滤器
            :param dic: 即将用于创建新对象的字典
            :return:    可以直接创建新对象的字典
            '''
            for k, v in dic.items():
                if '__' in k or str(k) == 'id' or isinstance(v, dict) or str(k) == 'status':
                    '''当字段名为__扩展名,字段为id,字段值为字典,或者字典为状态字段,则排除'''
                    dic.pop(k)
            return dic

        defines = ProcessDefine.objects.filter(id=define_id)
        if defines.exists():
            define = defines.first()
            define_dict = define.serialize()
            with transaction.atomic():
                '''流程设计对象复制'''
                define_dict = __colation(define_dict)
                define_dict['own_entity_id'] = own_entity_id
                copy_define = ProcessDefine.objects.create(**define_dict)
                '''流程设计对象关联步骤复制'''
                steps = ProcessActivityConnectionDefine.objects.filter(process_define_id=define_id)
                copy_step_mapping = dict()
                for step in steps:
                    step_dict = step.serialize()
                    step_id = step_dict.pop('id')
                    step_dict = __colation(step_dict)
                    step_dict['process_define_id'] = copy_define.id
                    copy_step = ProcessActivityConnectionDefine.objects.create(**step_dict)
                    '''生成新旧同步骤对照关系表'''
                    copy_step_mapping[step_id] = copy_step.id
                '''步骤间关联关系复制,依赖新旧步骤关系对照表,查询获取对应关联关系'''
                connections = ActivityComplexConnectionDefine.objects.filter(Q(father_id__in=copy_step_mapping.keys()) |
                                                                             Q(child_id__in=copy_step_mapping.keys()))
                connection_pks = []
                copy_connections = []
                for connection in connections:
                    if connection.id not in connection_pks:
                        connection_dict = connection.serialize()
                        connection_pks.append(connection_dict.pop('id'))
                        connection_dict = __colation(connection_dict)
                        connection_dict['father_id'] = copy_step_mapping[connection_dict['father_id']]
                        connection_dict['child_id'] = copy_step_mapping[connection_dict['child_id']]
                        copy_connections.append(ActivityComplexConnectionDefine(**connection_dict))
                ActivityComplexConnectionDefine.objects.bulk_create(copy_connections)
                return True
        else:
            raise FlowException(u'目标模板不存在,请刷新页面!')

    @classmethod
    def my_tasks(cls, user_id, status=TaskStatus.RUNNING):
        tasks = FlowTask.objects.filter(owner=user_id, status=status)
        return [task.serialize() for task in tasks]


class TaskTimer(object):
    '''
        任务定时器
    '''

    def __init__(self):
        '''
            初始化:
                pool 持久化连接池,此处使用redis做持久化序列
                job_stores 任务仓库,使用redis任务仓库
                executors 执行器,默认使用线程执行
                job_defaults 任务默认参数
        '''

        self.pool = redis.ConnectionPool(host='127.0.0.1', port=6379)

        self.job_stores = dict(redis=RedisJobStore(connection_pool=self.pool))

        self.executors = dict(default=ThreadPoolExecutor(200),
                              processpool=ProcessPoolExecutor(10))

        self.job_defaults = dict(coalesce=True, max_instances=1, misfire_grace_time=60)

    def get_scheduler(self):
        '''
            获取任务调度器
        :return: 全新的任务调度器
        '''
        scheduler = BackgroundScheduler(jobstores=self.job_stores, executors=self.executors,
                                        job_defaults=self.job_defaults, timezone=utc)
        return scheduler

    def create_timer_task(self, func, params, task_id, run_time=None):
        '''
            创建定时任务
        :param func:            定时执行的方法
        :param params:          执行方法时传递的参数
        :param task_id:         任务id
        :param run_time:        运行时间
        '''
        scheduler = self.get_scheduler()
        if not run_time:
            run_time = (datetime.datetime.now() + datetime.timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")
        scheduler.add_job(func=func, trigger='date', kwargs=params, run_date=run_time,
                          id='workflow_task_' + str(task_id))
        scheduler.start()


class FlowException(Exception):

    def __init__(self, message=u'审批流异常'):
        self.code = 3403
        self.message = message