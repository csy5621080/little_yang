# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flows import *


class User(models):

    username = models.CharField(max_length=16, null=True, blank=True, verbose_name='用户名')
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name='密码')
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name='昵称')
    mobile = models.CharField(max_length=32, null=True, blank=True, default='', verbose_name='手机')
    email = models.CharField(max_length=255, null=True, blank=True, default='', verbose_name='邮箱')
    organization = models.CharField(max_length=255, default='', verbose_name='工作单位', null=True)
    job = models.CharField(max_length=128, blank=True, null=True, default='', verbose_name='职务')

    entity = models.ForeignKey('Entity', blank=True, null=True, on_delete=models.CASCADE, verbose_name='机构')

    user_type = models.CharField(max_length=255, blank=True, default='EXA', verbose_name="用户类型")

    class Meta:
        ordering = ['id']


class Entity(models):

    name = models.CharField(max_length=127, default='', verbose_name='名字')
    level = models.IntegerField(null=True, blank=True, verbose_name='等级')

    class Meta:
        ordering = ['id']


class Project(models, FlowBase):

    name = models.CharField(max_length=255, default='', verbose_name='名字')
    gov_name = models.CharField(max_length=255, default='', verbose_name="实施机构名称")
    company_name = models.CharField(max_length=255, default='', verbose_name="项目公司名称")
    supervisor_name = models.CharField(max_length=255, default='', verbose_name="监理单位名称")
    amount = models.FloatField(null=True, verbose_name='项目金额')
    duration = models.FloatField(null=True, verbose_name='拟合作期限')
    construct_duration = models.FloatField(null=True, verbose_name='建设期')
    bid_date = models.DateField(verbose_name='中标日期', null=True)
    construct_date = models.DateField(verbose_name='开工日期', null=True)
    operate_date = models.DateField(verbose_name='运营日期', null=True)
    attachments = models.TextField(null=True, verbose_name='项目附件')
    perf_entity = models.ForeignKey('Entity', blank=True, null=True, on_delete=models.CASCADE, verbose_name='机构')

    process_define = models.ForeignKey('ProcessDefine', blank=True, null=True, verbose_name='流程模板')
    self_flow = models.ForeignKey('Flow', related_name='self_flow', blank=True, null=True, verbose_name='自有流程')

    class Meta:
        ordering = ['id']

