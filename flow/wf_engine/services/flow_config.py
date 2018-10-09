# -*- coding: utf-8 -*-
from wf_engine.models import *
"""
instance_created 单个实例进程推进方法。
"""


''' 流程依托实体 '''
FLOW_ENTITY = [Entity, Project]

''' 用户实体 '''
USER_ENTITY = [User]

''' 事件依托实体 '''
# Todo
ACTIVITY_ENTITY = [(Project, '创建项目', 'instance_created', None),
                   (Flow, '流嵌套', 'instance_created', Flow.status.field_name),
                   (Opinion, '审批', 'instance_created', Opinion.comment.field_name)]