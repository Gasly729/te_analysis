# Species TE Result Contract

## Scope

这份合同文档定义当前 species downstream 输出的最小成功标准和结构边界。当前已验证成功的对象是：

- species root: `data/processed/te_species/Homo_sapiens`
- trial: `homo_sapiens_species_te_prepare`
- execution strategy: `serial-fallback`

这里的 `serial-fallback` 是项目自有执行策略，不修改 shared `vendor/TE_model` tracked files。

## Canonical output paths

当前 canonical output root：

- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare`

当前 canonical output files：

- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`
- `human_TE_cellline_all_T.csv`

## Required files

要判定 species Stage 2/3 成功，以下文件必须同时存在且非零：

- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`
- `human_TE_cellline_all_T.csv`

如果只生成前两者而没有第三个，只能视为 Stage 2 成功、Stage 3 未完成。

## Minimal success criteria

最小成功标准如下：

1. species trial 目录存在非空 Stage 1 输入：
   - `ribo_paired_count_dummy.csv`
   - `rna_paired_count_dummy.csv`
2. Stage 2 结束后，trial 目录下出现非空：
   - `human_TE_sample_level.rda`
   - `human_TE_cellline_all.csv`
3. Stage 3 结束后，trial 目录下出现非空：
   - `human_TE_cellline_all_T.csv`
4. Stage 2/3 日志中未见明确 `Traceback`、`serverSocket` 或文件缺失错误

## Structural expectations for each file

### `human_TE_sample_level.rda`

这是 Stage 2 的 R 数据对象文件。

当前只验证了：

- 文件存在
- 文件非零
- 它由当前成功的 Stage 2 路径产出

当前**没有**额外保证：

- 内部对象名称
- 内部矩阵维度
- 生物学正确性

### `human_TE_cellline_all.csv`

这是当前 species 结果的 canonical CSV。

在 `Homo_sapiens` 的已验证结果中，结构事实是：

- 形状：`4 x 11158`
- 行索引唯一
- 列名唯一
- 没有全 NA 列
- 没有全 NA 行
- 没有全零列
- 没有全零行

在当前结果里，它是后续受控分析更合适的直接消费对象。

### `human_TE_cellline_all_T.csv`

这是 shared vendor `src/transpose_TE.py` 产出的转置版本。

在 `Homo_sapiens` 的已验证结果中，结构事实是：

- 形状：`11158 x 4`
- 列名唯一
- 没有全 NA 列
- 没有全 NA 行
- 没有全零列
- 没有全零行
- 它与 `human_TE_cellline_all.csv` 的转置结果在数值和轴顺序上匹配

但必须明确：

- 它的行名**不是唯一的**
- 当前已验证有 `16` 个重复行名
- 这是 shared vendor `transpose_TE.py` 对转置后索引做 `str.replace("\\.(.*)", "", regex=True)` 的直接结果

因此：

- `human_TE_cellline_all_T.csv` 可以作为便捷视图使用
- 但如果下游分析要求 feature ID 全局唯一，不应在未处理重复行名的前提下直接把它当成唯一键矩阵

## What counts as failure

以下任一情况都应判为失败或未完成：

- 任一 required file 缺失
- 任一 required file 为 0 字节
- Stage 2 日志中出现：
  - `serverSocket`
  - `creation of server socket failed`
  - `Traceback`
  - 明确文件缺失错误
- Stage 3 日志中出现 Python traceback 或输出文件缺失
- `human_TE_cellline_all.csv` 或 `human_TE_cellline_all_T.csv` 出现全空或全零的整列 / 整行

## What later analysis may consume directly

当前允许直接消费的对象：

- `human_TE_cellline_all.csv`
  - 适合做后续受控分析入口
- `human_TE_sample_level.rda`
  - 适合在 R 侧继续做对象级检查或下游处理，但当前合同不定义其内部 schema

当前不建议无条件直接依赖的对象：

- `human_TE_cellline_all_T.csv`
  - 只能在接受重复行名风险的前提下直接用
  - 若要求唯一 feature key，应先做重复项处理

## What is still not guaranteed

当前 success **不保证**：

- 生物学解释正确性
- 统计结果优劣
- 跨物种可直接外推
- `shared` 模式在当前主机可直接成功
- `human_TE_cellline_all_T.csv` 的行名全局唯一

当前 success **已明确保证**：

- `Homo_sapiens` 的 species serial-fallback 路径已真实闭环
- shared `vendor/TE_model` tracked files 未被修改
- `aggregate_species_te.py` 仍保持 prepare-only 设计
