# 智能客服系统 v0.2

基于 OpenAI API 的智能客服系统，支持多会话管理和销售数据查询。

## 功能特点

- 多会话管理
- 销售数据智能查询
- 上下文理解
- 结构化查询日志
- 数据库持久化

## 技术栈

- Python 3.8+
- Streamlit
- OpenAI API
- PyMySQL
- MySQL

## 安装

1. 克隆仓库
```bash
git clone [repository-url]
cd [project-name]
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置
复制 `config/config.example.json` 到 `config/config.json` 并填写配置：
```json
{
  "mysql": {
    "host": "localhost",
    "database": "chatbot",
    "user": "your_username",
    "password": "your_password",
    "pool_size": 5
  },
  "openai": {
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7
  }
}
```

4. 运行
```bash
streamlit run app.py
```

## 更新日志

### v0.2
- 优化数据库连接管理
- 改进查询参数处理
- 增强错误处理
- 完善日志记录

### v0.1
- 基础多会话支持
- 简单的销售数据查询
- 基本的对话功能

## 贡献

欢迎提交 Pull Request 或创建 Issue。

## 许可

MIT License