from method import rpc

task_id = "xform_relic"
status = rpc("xform.get_status", {"task_id": task_id})
print(status)
# print(rpc("xform.list_tasks", {"profile_id": "demo"}))
