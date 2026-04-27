# TRMS

同济大学 ACM 竞赛报销收集系统。

当前开发切片聚焦后端基础能力：报销任务创建、查询和状态管理骨架。

## 本地验证

```bash
uv sync
uv run pytest
uv run uvicorn trms_backend.main:app --reload
```

