# -*- coding: utf-8 -*-
from django.db import models


class FlowBase(models.Model):

    task = models.ForeignKey('FlowTask', blank=True, null=True, verbose_name='任务id')
    flow = models.ForeignKey('Flow', blank=True, null=True, verbose_name='流程id')
    owner = models.ForeignKey('User', blank=True, null=True, verbose_name='所有人')

    class Meta:
        abstract = True


class Flow(models):

    '''流程实例'''

    entity = models.ForeignKey('Entity', null=True, blank=True, verbose_name='主体')

    process_define = models.ForeignKey('ProcessDefine', verbose_name='流程设计id')

    process_start_time = models.DateTimeField(verbose_name='开始日期', null=True)

    flow_info = models.TextField(null=True, blank=True, verbose_name='流json')

    next_step = models.CharField(max_length=512, null=True, blank=True, verbose_name='下一步名称')

    next_step_name = models.CharField(max_length=512, null=True, blank=True, verbose_name='下一步名称(显示)')

    last_step = models.CharField(max_length=512, null=True, blank=True, verbose_name='最新完成步骤名称')

    rely_pk = models.IntegerField(null=True, blank=True, verbose_name='依赖对象id')

    rely_instance = models.CharField(max_length=512, null=True, blank=True, verbose_name='依赖对象')

    STATUS_TYPE = (
        (0, '等待'),
        (1, '激活'),
        (2, '完成'),
    )

    status = models.IntegerField(default=0, verbose_name='状态')

    name = models.CharField(max_length=512, null=True, blank=True, verbose_name='名字')

    flow_id = models.IntegerField(null=True, blank=True, verbose_name='父流程id')
    task_id = models.IntegerField(null=True, blank=True, verbose_name='从属任务id')
    owner_id = models.IntegerField(null=True, blank=True, verbose_name='从属任务所有人')

    class Meta:
        ordering = ['id']


class FlowTask(models):

    ''' 任务 '''

    flow = models.ForeignKey('Flow', verbose_name='流程实例')

    name = models.CharField(max_length=128, null=True, blank=True, verbose_name='名称')

    owner = models.CharField(max_length=512, null=True, blank=True, verbose_name='任务所有人')

    STATUS_TYPE = (
        (0, '等待'),
        (1, '就绪'),
        (2, '完成'),
        (3, '重定向(驳回至某处)'),
        (4, '中止')
    )

    status = models.IntegerField(default=0, verbose_name='状态')

    update_time = models.DateTimeField(null=True, blank=True, verbose_name='状态更改时间')

    step = models.ForeignKey('ProcessActivityConnectionDefine', verbose_name='事件')

    step_num = models.IntegerField(default=0, verbose_name='步骤数')

    t_id = models.CharField(max_length=512, null=True, blank=True, verbose_name='TID')

    trigger_time = models.DateTimeField(null=True, blank=True, verbose_name='触发时间')

    class Meta:
        ordering = ['id']


class UserScore(models):

    ''' 用户打分实例（测试用，上线删除） '''

    flow = models.ForeignKey('Flow', null=True, blank=True, verbose_name='流程')

    task = models.ForeignKey('FlowTask', null=True, blank=True, verbose_name='任务')

    user = models.ForeignKey('User', null=True, blank=True, verbose_name='打分人')

    class Meta:
        ordering = ['id']


class Opinion(models, FlowBase):

    project = models.ForeignKey('Project', null=True, blank=True, verbose_name='项目')

    COMMENT_TYPE = (
        (1, '同意'),
        (2, '驳回')
    )

    comment = models.IntegerField(null=True, blank=True, verbose_name='审批意见')

    class Meta:
        ordering = ['id']