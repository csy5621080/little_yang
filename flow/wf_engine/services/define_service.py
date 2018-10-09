# -*- coding: utf-8 -*-
import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flow.settings")
django.setup()
from wf_engine.models import *


def make_complex_spec(process_id):

    ProcessDefine.objects.filter(id=process_id).update(status=1)

    return True


def check_define(process_define_id):
    try:
        # TODO: 流程设计检查，1.起始动作设定，2.结束动作设定，3.死循环判定及处理  ...
        ProcessDefine.objects.get(id=process_define_id)
        pass
    except Exception as e:
        raise e


def release_flow_define(process_define_id):
    # 流程发布
    if make_complex_spec(process_define_id):
        return True
