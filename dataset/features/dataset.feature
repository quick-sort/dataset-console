# language: zh-CN
功能: 数据集管理设计约束

  # ===== dataset.source 约束 =====

  场景: source.code 必须唯一
    假设 已存在 code="github" 的 dataset.source 记录
    当 用户尝试创建另一个 code="github" 的记录
    那么 系统应拒绝创建
    并且 抛出约束错误 "Source code must be unique!"

  场景: source.name 必须唯一
    假设 已存在 name="GitHub" 的 dataset.source 记录
    当 用户尝试创建另一个 name="GitHub" 的记录
    那么 系统应拒绝创建
    并且 抛出约束错误 "Source name must be unique!"

  # ===== dataset.package 约束 =====

  场景: package.code 在同级 parent_id 下必须唯一
    假设 package "ml" 下已存在 code="pytorch" 的子包
    当 用户尝试在同一 parent_id 下创建另一个 code="pytorch" 的子包
    那么 系统应拒绝创建
    并且 抛出约束错误 "Package code must be unique within same parent!"

  场景: package.name 在同级 parent_id 下必须唯一
    假设 package "ml" 下已存在 name="PyTorch" 的子包
    当 用户尝试在同一 parent_id 下创建另一个 name="PyTorch" 的子包
    那么 系统应拒绝创建
    并且 抛出约束错误 "Package name must be unique within same parent!"

  场景: package 支持层级树结构
    假设 用户创建 package 层级: "机器学习" -> "深度学习" -> "大语言模型"
    那么 每个包的 parent_path 应包含完整路径
    并且 可以通过 parent_path 进行树形查询

  # ===== dataset 约束 =====

  场景: dataset.name 在同 source_id 下必须唯一
    假设 dataset.source "github" 下已存在 name="训练集" 的 dataset
    当 用户在同一 source_id 下创建另一个 name="训练集" 的 dataset
    那么 系统应拒绝创建
    并且 抛出约束错误 "Dataset name must be unique per source!"

  场景: dataset.code 在同 source_id 下必须唯一
    假设 dataset.source "github" 下已存在 code="train" 的 dataset
    当 用户在同一 source_id 下创建另一个 code="train" 的 dataset
    那么 系统应拒绝创建
    并且 抛出约束错误 "Dataset code must be unique per source!"

  场景: dataset.source_id 为必填字段
    当 用户创建 dataset 时不填写 source_id
    那么 系统应阻止保存
    并且 source_id 字段显示为必填

  场景: dataset 支持多种 chunk_type
    当 用户创建 dataset 并选择 chunk_type
    那么 系统应支持以下类型:
      | chunk_type |
      | pdf        |
      | csv        |
      | docx       |
      | xlsx       |
      | json       |
      | jsonl      |
      | parquet    |

  # ===== dataset.data_chunk 约束 =====

  场景: data_chunk.key 在同 dataset_id 下必须唯一
    假设 dataset "训练集" 下已存在 key="github/train/001.csv" 的 data_chunk
    当 用户在同一 dataset_id 下创建另一个 key="github/train/001.csv" 的记录
    那么 系统应拒绝创建
    并且 抛出约束错误 "Chunk key must be unique within dataset!"

  场景: data_chunk.key 由 dataset 自动计算生成
    假设 创建 dataset，配置 key_fields=["split", "shard"]
    并且 dataset.source_id.code="github"，dataset.code="train"，dataset.chunk_type="csv"
    当 创建 data_chunk 且 metadata={"split": "train", "shard": "001"}
    那么 data_chunk.key 应自动生成为 "github/train/train/001.csv"

  场景: data_chunk.state 初始值为 missing
    当 创建新的 data_chunk 记录
    那么 state 默认值为 "missing"
    并且 state 可选值包括: missing, exists, checked

  场景: data_chunk.metadata 为有效 JSON
    当 用户编辑 data_chunk.metadata
    那么 必须输入有效的 JSON 格式
    并且 使用 json_editor 组件编辑

  场景: data_chunk 删除受 dataset_id.ondelete='restrict' 限制
    假设 data_chunk 关联到 dataset
    当 用户尝试删除该 dataset
    那么 系统应阻止删除
    并且 提示存在关联的数据块

  # ===== build_chunk_key 方法约束 =====

  场景: build_chunk_key 需要 source_id.code, code, chunk_type
    假设 dataset 缺少 source_id 或 source_id.code 为空
    当 调用 build_chunk_key
    那么 应抛出 ValueError
    并且 错误信息包含 "source code, dataset code, and chunk data type are required"

  场景: build_chunk_key 带 key_fields 时使用元数据拼接路径
    假设 dataset 的 key_fields=["split", "shard"]
    并且 metadata={"split": "train", "shard": "002"}
    当 调用 build_chunk_key(metadata)
    那么 返回 "source_code/dataset_code/train/002.chunk_type"

  场景: build_chunk_key 不带 key_fields 时直接生成键
    假设 dataset 的 key_fields 为空或 False
    当 调用 build_chunk_key
    那么 返回 "source_code/dataset_code.chunk_type"

  # ===== parse_chunk_key 方法约束 =====

  场景: parse_chunk_key 验证键格式
    当 调用 parse_chunk_key("invalid-key")
    那么 应抛出 ValueError
    并且 错误信息包含 "invalid key format"

  场景: parse_chunk_key 提取键的各部分
    假设 调用 parse_chunk_key("github/train/split1/001.csv", key_fields=["split", "id"])
    那么 应返回:
      | 字段         | 值                    |
      | source_code   | github                |
      | dataset_code  | train                 |
      | chunk_type   | csv                   |
      | metadata     | {"split": "split1", "id": "001"} |

  场景: parse_chunk_key 验证 key_fields 长度匹配
    假设 键为 "github/train/001.csv"
    并且 key_fields=["split", "shard"]（长度为2）
    当 调用 parse_chunk_key
    那么 应抛出 ValueError
    并且 错误信息包含 "key_fields length mismatch"

  # ===== scan_chunks 方法约束 =====

  场景: scan_chunks 需要配置 dataset.storage_id
    假设 dataset 未配置 storage_id
    当 调用 scan_chunks
    那么 应抛出 ValueError
    并且 错误信息包含 "no storage configured"

  场景: scan_chunks 跳过已存在的 chunk
    假设 dataset.chunk_ids 中已存在 key="github/train/001.csv"
    并且 storage.list_keys() 返回包含该键的列表
    当 调用 scan_chunks
    那么 不应重复创建已存在的 chunk

  场景: scan_chunks 创建新的 chunk
    假设 storage.list_keys() 返回 ["github/train/001.csv", "github/train/002.csv"]
    并且 dataset.chunk_ids 为空
    当 调用 scan_chunks
    那么 应创建2个新的 data_chunk 记录
    并且 返回值应为 2

  # ===== fill_rate 计算约束 =====

  场景: fill_rate = chunk_ids 数量 / manifest.total_chunks
    假设 dataset.manifest_id.total_chunks = 100
    并且 dataset.chunk_ids 数量 = 75
    那么 dataset.fill_rate 应计算为 0.75

  场景: 无 manifest 时 fill_rate 为 0
    假设 dataset.manifest_id 为空
    那么 dataset.fill_rate 应为 0

  场景: manifest.total_chunks 为 0 时 fill_rate 为 0
    假设 dataset.manifest_id.total_chunks = 0
    那么 dataset.fill_rate 应为 0（避免除零错误）

  # ===== total_chunks 计算约束 =====

  场景: total_chunks = len(chunk_ids)
    假设 dataset.chunk_ids 包含5个记录
    那么 dataset.total_chunks 应为 5