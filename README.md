# HallSpan 考场间距排座

在考室网格上按最小曼哈顿距离排座，同试卷套不得四邻相邻，并输出违规与统计。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4900 |
| API | http://localhost:9900 |
| API 文档 | http://localhost:9900/docs |
| Postgres | localhost:5450 |

健康检查：`GET http://localhost:9900/api/health`

## 使用说明

1. 在「考室」「考生」「试卷套」确认基础数据。
2. 在「试卷套」设置主卷、各套人数上限与主卷人数下限：
   - 上限：该套最多入座人数，触顶后即使有空位也不再塞同套（未排原因「同卷人数已满」）；0 表示不截断。
   - 下限：主卷已座人数低于下限则整场排座失败（「主卷人数不足」），不生成方案，辅卷人数不计入保底；0 表示关闭保底。
   - 上下限不允许负值；修改后再排座按新值出图，旧方案自动失效。
3. 打开「排座图」执行间距排座。
4. 在「违规」查看间距或同卷相邻问题与未排原因。
5. 在「统计」查看占用、违规与各套已座/未排汇总（与名册、排座图同源对齐）。

## 开发与测试

```bash
docker compose exec api pytest -q
```
