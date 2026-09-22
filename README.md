# 前后端分离计算器后端

## 项目介绍

基于 Python 标准库的计算器 API。后端负责表达式校验、解析、计算、异常处理和历史记录持久化，
前端只通过 HTTP/JSON 接口提交表达式并读取结果。

支持加、减、乘、除、括号、运算优先级、一元正负号和小数。成功计算会写入数据库，
非法表达式和除以零不会生成历史记录。

## 技术栈

- Python 3.10 或更高版本
- `http.server`：HTTP/JSON API
- `sqlite3`：历史记录持久化
- `decimal`：精确的小数计算
- `unittest`：自动化测试

项目不需要 `pip install`，也不需要创建虚拟环境。

## 安装与启动

在 `backend` 目录执行：

```powershell
python -m app.server
```

API 默认监听 `http://127.0.0.1:8000`，启动时会自动创建 SQLite 表。

## 配置

复制 `.env.example` 为 `.env` 后按需修改。程序也会直接读取系统环境变量。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_PATH` | `backend/data/calculator.db` | SQLite 数据库文件路径 |
| `ALLOWED_ORIGINS` | 本地前端地址 | 允许跨域的前端来源，多个地址用逗号分隔 |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8000` | 服务监听端口 |

## 数据库初始化

服务首次启动时会自动创建 `calculation_history` 表，字段包括 `id`、`expression`、
`result` 和 `created_at`。表结构使用 `CREATE TABLE IF NOT EXISTS`，重复启动不会重复创建。

## API

- `POST /api/calculations`：计算并保存表达式。
- `GET /api/history`：按时间倒序读取全部历史。
- `DELETE /api/history/{id}`：删除指定历史记录。
- `GET /api/health`：健康检查。

计算请求示例：

```json
{"expression": "(1+2)*3"}
```

成功响应示例：

```json
{
  "success": true,
  "data": {
    "id": 1,
    "expression": "(1+2)*3",
    "result": 9,
    "createdAt": "2026-09-22T14:00:00Z"
  }
}
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

## Render 部署

1. 将本仓库推送到独立 GitHub 仓库。
2. 在 Render 中使用仓库内的 `render.yaml` 创建 Blueprint。
3. 把 `render.yaml` 中的 `YOUR_GITHUB_USERNAME` 替换为实际用户名。
4. 等待 Web Service 与持久磁盘创建完成。
5. 访问 `https://你的服务地址/api/health`，确认返回成功。
6. 把服务地址写入前端 `config.js` 的 `API_BASE_URL`。

`render.yaml` 使用 `starter` 计划和 1 GB 持久磁盘。SQLite 文件放在
`/var/data/calculator.db`，服务重启或重新部署后历史仍然保留。

Render 免费实例的文件系统是临时的，不适合保存 SQLite 文件。如果必须控制成本，
可以改用自己的云服务器或始终在线的本地/校园环境。
