# -*- coding: utf-8 -*-
from django.db import models


class ProcessDefine(models):

    name = models.CharField(max_length=128, verbose_name='流程名称')

    info = models.TextField(verbose_name='流程json')

    TYPES = (
        (1, '工作流'),
        (2, '审批流'),
    )

    type = models.IntegerField(default=1, choices=TYPES, verbose_name='流程类型')

    STATUS = (
        (0, '未确认'),
        (1, '已确认')
    )
    status = models.IntegerField(default=0, verbose_name='状态')

    own_entity = models.ForeignKey('Entity', null=True, blank=True, verbose_name='所属实体')  # 为空则为明树模板

    class Meta:
        ordering = ['id']


class ActivityDefine(models):

    FUNC_CHOICES = (
        ('ConditionActivity', '条件动作'),
        ('FuncActivity', '方法调用动作')
    )

    func_name = models.CharField(max_length=128, choices=FUNC_CHOICES, verbose_name='对应方法', null=True, blank=True)

    params = models.CharField(max_length=128, verbose_name='参数', null=True, blank=True)

    name = models.CharField(max_length=128, verbose_name='动作名称', null=True, blank=True)

    custom_expression = models.CharField(max_length=1024, verbose_name='自定义表达式', null=True, blank=True)

    class_module = models.CharField(max_length=512, verbose_name='类路径', null=True, blank=True)

    instance_model = models.CharField(max_length=512, verbose_name='对应实例', null=True, blank=True)

    pick_field = models.CharField(max_length=512, null=True, blank=True, verbose_name='选取字段')

    class Meta:
        ordering = ['id']


class PushCondition(models):

    fields = []

    func_name = models.CharField(max_length=128, verbose_name='对应方法名称')

    params = models.CharField(max_length=128, verbose_name='参数')

    code = models.CharField(max_length=128, null=True, blank=True, verbose_name='编码')

    name = models.CharField(max_length=128, verbose_name='动作名称')

    func_module = models.CharField(max_length=512, verbose_name='方法路径', null=True, blank=True)

    class Meta:
        ordering = ['id']


class ProcessActivityConnectionDefine(models):

    process_define = models.ForeignKey(ProcessDefine, verbose_name='流程')

    activity_define = models.ForeignKey(ActivityDefine, verbose_name='步骤', null=True, blank=True)

    condition = models.ForeignKey(PushCondition, verbose_name='本步推进条件', null=True, blank=True)

    pre_activity = models.ForeignKey('self', related_name='father_connection', null=True, blank=True, verbose_name='上一步')

    name = models.CharField(max_length=128, null=True, blank=True, verbose_name='名称')

    owner = models.ForeignKey('User', null=True, blank=True, verbose_name='所属人')

    condition_result = models.CharField(max_length=128, null=True, blank=True, verbose_name='条件结果')

    complex_pre = models.CharField(max_length=512, null=True, blank=True, verbose_name='复杂情况下的关联表达式')

    RELATION_TYPE = (
        ('And', '同时满足'),
        ('Or', '有一个满足')
    )

    arrival_condition = models.CharField(max_length=512, default='And', choices=RELATION_TYPE, verbose_name='关联关系')

    nest_define = models.ForeignKey('ProcessDefine', related_name='nest_flow', null=True, blank=True,
                                    verbose_name='嵌套流设计')

    class Meta:
        ordering=['id']


class ActivityComplexConnectionDefine(models):

    father = models.ForeignKey(ProcessActivityConnectionDefine, related_name='father', verbose_name='父步骤')

    child = models.ForeignKey(ProcessActivityConnectionDefine, related_name='child', verbose_name='子步骤')

    condition = models.ForeignKey(PushCondition, verbose_name='推进条件', null=True, blank=True)

    condition_params = models.CharField(max_length=128, null=True, blank=True, verbose_name='条件参数')

    condition_result = models.CharField(max_length=128, null=True, blank=True, verbose_name='条件结果')

    RELATION_TYPE = (
        ('And', '同时满足'),
        ('Or', '有一个满足')
    )

    relation = models.CharField(max_length=512, default='And', verbose_name='关联关系')

    class Meta:
        ordering = ['id']


class Action(models):

    name = models.CharField(max_length=128, verbose_name='动作')

    func_name = models.CharField(max_length=512, verbose_name='调用方法')

    params = models.CharField(max_length=512, verbose_name='参数')

    class Meta:
        ordering = ['id']
