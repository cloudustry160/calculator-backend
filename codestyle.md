# 后端代码规范

## 规范来源

本规范参考 [PEP 8](https://peps.python.org/pep-0008/) 与
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。
项目不依赖第三方代码检查工具，提交前使用标准库测试和人工检查。

## 基本规则

- 使用 4 个空格缩进，禁止使用 Tab。
- 单行代码长度不超过 88 个字符。
- 模块、函数和变量使用 `snake_case`，类名使用 `PascalCase`。
- 导入按标准库、项目模块分组，组与组之间保留一个空行。
- 公共函数和复杂逻辑必须写明类型标注。
- 接口响应统一使用 `ApiResponse` 构造，保持状态码、响应体和响应头结构一致。
- 数据库记录和历史记录等结构化数据使用 `dataclass` 或明确的字典结构，字段命名保持稳定。
- 数据库操作统一通过 `Database` 类执行，每个请求使用独立 SQLite 连接。
- 禁止使用 `eval`、`exec` 或类似方式执行用户输入。
- 提交前运行 `python -m unittest discover -s tests -v`。
