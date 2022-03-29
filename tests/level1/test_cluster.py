import skitai
import conftest
from skitai.protocols.sock.asynconnect import AsynConnect
from skitai.tasks.httpbase import task

def test_task (wasc):
    cluster = wasc.clusters_for_distcall ["example"]
    origin = cluster._conn_class
    cluster._conn_class = AsynConnect
    cdc  = task.Task (cluster, "/index")
    cluster._conn_class = origin
