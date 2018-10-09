
# -*- coding: utf-8 -*-
import importlib
from wf_engine.models import *
''' 表达式方法 '''

# ----------------------------------------filter func ------------------------------------------------------


def get_model(module_name, instance):
    return getattr(importlib.import_module(module_name), instance)


def instance_created(task_id, owner=None):
    '''
        获取对象     if owner = None : sys ,    系统所有
                    else owner = user          特定用户所有
        对应对象名称  instance_name
        对应对象路径  module_name
        对应任务id   task_id
        检取对象属性  pick_field default=id      默认获取id
    :return:
    '''
    task = FlowTask.objects.get(id=task_id)
    module_name = task.step.activity_define.class_module
    instance_name = task.step.activity_define.instance_model
    pick_field = task.step.activity_define.pick_field
    model = get_model(module_name, instance_name)
    instance = model.objects.filter(task_id=task_id) if not owner else model.objects.filter(task_id=task_id, owner_id=owner)
    if instance:
        if pick_field:
            return getattr(instance.order_by('-id').first(), pick_field)
        else:
            return getattr(instance.order_by('-id').first(), 'id')


def flow_nest(task_id, owner=None):
    '''
        审批流嵌套
    :param task_id:     任务id
    :param owner:       所有人
    :return:
    '''
    pass


# -----------------------------------------task func ----------------------------------------------------

TASK_FUNC = ['more_than', 'less_than', 'equal', 'exist', 'not_exist']


def more_than(score, condition_result):
    """大于"""
    if score > condition_result:
        return True
    return False


def less_than(score, condition_result):
    """小于"""
    if score < condition_result:
        return True
    return False


def equal(score, condition_result):
    """等于"""
    if score == condition_result:
        return True
    return False


def exist(score, condition_result):
    """ 存在 """
    if score is None or len(str(score)) == 0:
        return False
    return True


def not_exist(score, condition_result):
    ''' 不存在 '''
    if score is None or len(score) == 0:
        return True
    return False