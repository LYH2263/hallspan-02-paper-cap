import os
import tempfile

# 必须在导入 app 之前指向测试库, 否则 engine 会绑定默认 Postgres
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp(prefix='hallspan_test_')}/test.db")
