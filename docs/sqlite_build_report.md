# P1 sqlite 构造报告

日期：2026-04-20
vendor SHA：b918e75f877262dca96665d18c3b472675f30a6d

## 1. references.yaml 已支持物种清单
共 4 个。

| 物种（lower-case key） |
| --- |
| arabidopsis thaliana |
| caenorhabditis elegans |
| homo sapiens |
| mus musculus |

## 2. metadata 中出现的物种 × 覆盖情况
| organism (原值) | normalized | supported? | sample 数 | experiment 数 | study 数 |
| --- | --- | --- | --- | --- | --- |
| Mus musculus | mus musculus | yes | 1610 | 727 | 28 |
| Homo sapiens | homo sapiens | yes | 817 | 745 | 39 |
| Saccharomyces cerevisiae | saccharomyces cerevisiae | no | 650 | 527 | 24 |
| Danio rerio | danio rerio | no | 430 | 51 | 2 |
| Escherichia coli | escherichia coli | no | 103 | 89 | 6 |
| Drosophila melanogaster | drosophila melanogaster | no | 54 | 52 | 3 |
| Staphylococcus aureus | staphylococcus aureus | no | 54 | 16 | 1 |
| Rattus norvegicus | rattus norvegicus | no | 52 | 52 | 4 |
| Zea mays | zea mays | no | 52 | 52 | 1 |
| Schizosaccharomyces pombe | schizosaccharomyces pombe | no | 38 | 38 | 2 |
| Trypanosoma brucei | trypanosoma brucei | no | 36 | 36 | 2 |
| Arabidopsis thaliana | arabidopsis thaliana | yes | 32 | 32 | 4 |
| D. melanogaster | d. melanogaster | no | 27 | 27 | 1 |
| Soybean | soybean | no | 20 | 20 | 1 |
| Streptomyces clavuligerus | streptomyces clavuligerus | no | 20 | 20 | 1 |
| Plasmodium falciparum | plasmodium falciparum | no | 20 | 10 | 1 |
| Rat | rattus norvegicus | no | 18 | 18 | 1 |
| danio rerio | danio rerio | no | 18 | 18 | 1 |
| Caenorhabditis briggsae | caenorhabditis briggsae | no | 12 | 12 | 1 |
| Caenorhabditis elegans | caenorhabditis elegans | yes | 12 | 12 | 1 |
| Caenorhabditis remanei | caenorhabditis remanei | no | 12 | 12 | 1 |
| Caenorhabitis brenneri | caenorhabitis brenneri | no | 12 | 12 | 1 |
| Saccharomyces paradoxus | saccharomyces paradoxus | no | 11 | 11 | 2 |
| Human | human | no | 10 | 10 | 1 |
| Arabidopsis | arabidopsis | no | 8 | 8 | 1 |
| Caenorhaboditis elegans | caenorhaboditis elegans | no | 8 | 8 | 1 |
| Saccharomyces uvarum | saccharomyces uvarum | no | 8 | 8 | 1 |
| Leishmania donovani | leishmania donovani | no | 6 | 6 | 1 |
| Xenopus laevis | xenopus laevis | no | 6 | 6 | 1 |
| Candida albicans | candida albicans | no | 5 | 2 | 1 |
| Saccharomyces cerevisiae* Saccharomyces paradoxus | saccharomyces cerevisiae* saccharomyces paradoxus | no | 4 | 4 | 1 |
| Mouse | mouse | no | 3 | 3 | 1 |

## 3. 受阻塞的 study 清单（物种未覆盖）
| GSE | organism | Ribo-Seq 样本数 | RNA-Seq 样本数 | 备注 |
| --- | --- | --- | --- | --- |
| E-MTAB-6231 | Rat | 10 | 8 | not in references.yaml |
| GSE102376 | Schizosaccharomyces pombe | 18 | 18 | not in references.yaml |
| GSE103421 | Escherichia coli | 16 | 32 | not in references.yaml |
| GSE103667 | Mouse | 1 | 2 | not in references.yaml |
| GSE104028 | Arabidopsis | 6 | 2 | not in references.yaml |
| GSE104506 | Saccharomyces cerevisiae | 9 | 9 | not in references.yaml |
| GSE106448 | Escherichia coli | 4 | 4 | not in references.yaml |
| GSE107718 | Saccharomyces cerevisiae | 20 | 4 | not in references.yaml |
| GSE108778 | Saccharomyces cerevisiae | 52 | 72 | not in references.yaml |
| GSE109343 | Saccharomyces cerevisiae | 4 | 10 | not in references.yaml |
| GSE111255 | Saccharomyces cerevisiae | 16 | 16 | not in references.yaml |
| GSE114892 | Saccharomyces cerevisiae | 14 | 14 | not in references.yaml |
| GSE115162 | Saccharomyces cerevisiae | 14 | 21 | not in references.yaml |
| GSE119454 | Escherichia coli | 4 | 4 | not in references.yaml |
| GSE122039 | Saccharomyces cerevisiae | 9 | 9 | not in references.yaml |
| GSE124204 | Saccharomyces cerevisiae | 3 | 4 | not in references.yaml |
| GSE125038 | Saccharomyces cerevisiae | 28 | 28 | not in references.yaml |
| GSE128136 | Rattus norvegicus | 10 | 2 | not in references.yaml |
| GSE128216 | Streptomyces clavuligerus | 8 | 12 | not in references.yaml |
| GSE13750 | Saccharomyces cerevisiae | 14 | 7 | not in references.yaml |
| GSE34082 | Saccharomyces cerevisiae | 37 | 33 | not in references.yaml |
| GSE34743 | Danio rerio | 24 | 20 | not in references.yaml |
| GSE45785 | Human | 4 | 6 | not in references.yaml |
| GSE48140 | Caenorhabditis briggsae | 6 | 6 | not in references.yaml |
| GSE48140 | Caenorhabditis remanei | 6 | 6 | not in references.yaml |
| GSE48140 | Caenorhabitis brenneri | 6 | 6 | not in references.yaml |
| GSE49197 | Drosophila melanogaster | 8 | 2 | not in references.yaml |
| GSE51164 | Saccharomyces cerevisiae | 2 | 2 | not in references.yaml |
| GSE51532 | Saccharomyces cerevisiae | 6 | 6 | not in references.yaml |
| GSE52119 | Saccharomyces paradoxus | 2 | 5 | not in references.yaml |
| GSE52119 | Saccharomyces cerevisiae | 2 | 2 | not in references.yaml |
| GSE52119 | Saccharomyces cerevisiae* Saccharomyces paradoxus | 2 | 2 | hybrid/multi-species |
| GSE52236 | Candida albicans | 3 | 2 | not in references.yaml |
| GSE52799 | Drosophila melanogaster | 12 | 11 | not in references.yaml |
| GSE52809 | danio rerio | 9 | 9 | not in references.yaml |
| GSE52809 | Xenopus laevis | 3 | 3 | not in references.yaml |
| GSE52809 | Schizosaccharomyces pombe | 1 | 1 | not in references.yaml |
| GSE52968 | Saccharomyces cerevisiae | 9 | 1 | not in references.yaml |
| GSE53313 | Saccharomyces cerevisiae | 1 | 1 | not in references.yaml |
| GSE53693 | Danio rerio | 254 | 132 | not in references.yaml |
| GSE53767 | Escherichia coli | 8 | 2 | not in references.yaml |
| GSE55400 | Saccharomyces cerevisiae | 4 | 4 | not in references.yaml |
| GSE56372 | Escherichia coli | 12 | 12 | not in references.yaml |
| GSE56622 | Saccharomyces cerevisiae | 17 | 22 | not in references.yaml |
| GSE57336 | Trypanosoma brucei | 9 | 9 | not in references.yaml |
| GSE58402 | Plasmodium falciparum | 10 | 10 | not in references.yaml |
| GSE60752 | Rattus norvegicus | 8 | 8 | not in references.yaml |
| GSE63789 | Saccharomyces cerevisiae | 5 | 5 | not in references.yaml |
| GSE66411 | Saccharomyces cerevisiae | 14 | 14 | not in references.yaml |
| GSE66580 | Soybean | 10 | 10 | not in references.yaml |
| GSE67387 | Saccharomyces cerevisiae | 57 | 24 | not in references.yaml |
| GSE67387 | Caenorhaboditis elegans | 4 | 4 | not in references.yaml |
| GSE69414 | Saccharomyces cerevisiae | 2 | 1 | not in references.yaml |
| GSE72463 | Trypanosoma brucei | 9 | 9 | not in references.yaml |
| GSE72899 | Escherichia coli | 3 | 2 | not in references.yaml |
| GSE74197 | Staphylococcus aureus | 28 | 26 | not in references.yaml |
| GSE99920 | Drosophila melanogaster | 12 | 9 | not in references.yaml |
| PRJEB29208 | Rattus norvegicus | 10 | 10 | not in references.yaml |
| PRJNA306373 | D. melanogaster | 14 | 13 | not in references.yaml |
| PRJNA390293 | Saccharomyces uvarum | 3 | 5 | not in references.yaml |
| PRJNA390293 | Saccharomyces paradoxus | 1 | 3 | not in references.yaml |
| PRJNA390293 | Saccharomyces cerevisiae | 1 | 1 | not in references.yaml |
| PRJNA484227 | Rattus norvegicus | 2 | 2 | not in references.yaml |
| PRJNA495919. | Leishmania donovani | 3 | 3 | not in references.yaml |
| SRP133508 | Zea mays | 37 | 15 | not in references.yaml |

## 4. ETL drop 统计
- 因 matched RNA-Seq 缺失而 drop 的 experiment 数：0
- 因所有 experiment 被 drop 而 drop 的 study 数：0
- 缺失 `run` 而未写入 `metadata_srr` 的 run-level 行数：11
- 最终入库行数：study=120, experiment=2644, srr=4157

## 5. Smoke test 结果
- 选中的 study：GSE109122
- organism：Arabidopsis thaliana（normalized=`arabidopsis thaliana`）
- Ribo-Seq experiment 数：4
- matched RNA-Seq experiment 数：4
- 调用方式：方式 α（`generate_yaml.py --db /home/xrx/my_project/te_analysis/data/interim/snakescale/db.sqlite3`）
- generate_yaml.py 退出码：0
- 产出 YAML 路径：/tmp/smoke_project.yaml
- YAML 顶层 keys：alignment_arguments, clip_arguments, deduplicate, do_check_file_existence, do_fastqc, do_metadata, do_rnaseq, input, mapping_quality_cutoff, output, ribo, rnaseq
- `input.fastq` key 数：4
- `rnaseq.fastq` key 数：4
- 路径检查：8/8 个 FASTQ 路径都以 `_1.fastq.gz` 结尾，前缀模式为 `input/fastq/{GSE}/{GSM}/{SRR}_1.fastq.gz`
- 备注：vendor 当前实现里，`rnaseq.fastq` 的 key 复用了 Ribo-Seq 的 GSM key，而不是 RNA-Seq 自己的 experiment_alias
- 粘贴 YAML 前 80 行：

```yaml
alignment_arguments:
  filter: -L 15 --no-unal
  genome: --no-unal -k 1
  transcriptome: -L 15 --no-unal
clip_arguments: -u 1 --maximum-length=40 --minimum-length=15 --quality-cutoff=28 -a
  AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC --overlap=4 --trimmed-only
deduplicate: false
do_check_file_existence: true
do_fastqc: true
do_metadata: false
do_rnaseq: true
input:
  fastq:
    GSM2932477:
    - input/fastq/GSE109122/GSM2932477/SRR6466829_1.fastq.gz
    GSM2932478:
    - input/fastq/GSE109122/GSM2932478/SRR6466830_1.fastq.gz
    GSM2932479:
    - input/fastq/GSE109122/GSM2932479/SRR6466831_1.fastq.gz
    GSM2932480:
    - input/fastq/GSE109122/GSM2932480/SRR6466832_1.fastq.gz
  fastq_base: ''
  metadata:
    base: ''
    files: null
  reference:
    filter: reference/filter/arabidopsis/trna_rrna_seqs.fa*
    regions: reference/transcriptome/arabidopsis/mrna_regions_unique_genes.bed
    transcript_lengths: reference/transcriptome/arabidopsis/mrna_lengths_unique_genes.tsv
    transcriptome: reference/transcriptome/arabidopsis/mrna_seqs_unique_genes.fa*
  root_meta: ''
mapping_quality_cutoff: 20
output:
  individual_lane_directory: individual
  intermediates:
    alignment_ribo: alignment_ribo
    bam_to_bed: bam_to_bed
    base: intermediates/GSE109122
    clip: clip
    filter: filter
    genome_alignment: genome_alignment
    log: log
    quality_filter: quality_filter
    transcriptome_alignment: transcriptome_alignment
  merged_lane_directory: merged
  output:
    base: output/GSE109122
    fastqc: fastqc
    log: log
    ribo: ribo
ribo:
  coverage: true
  left_span: 35
  metagene_radius: 50
  read_length:
    max: 40
    min: 15
  ref_name: appris-v1
  right_span: 10
rnaseq:
  bt2_argumments: -L 15  --no-unal
  clip_arguments: -u 5 -l 40 --quality-cutoff=28 -a AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC
    --overlap=4
  deduplicate: false
  fastq:
    GSM2932477:
    - input/fastq/GSE109122/GSM2932481/SRR6466833_1.fastq.gz
    GSM2932478:
    - input/fastq/GSE109122/GSM2932482/SRR6466834_1.fastq.gz
    GSM2932479:
    - input/fastq/GSE109122/GSM2932483/SRR6466835_1.fastq.gz
    GSM2932480:
    - input/fastq/GSE109122/GSM2932484/SRR6466836_1.fastq.gz
  fastq_base: ''
  filter_arguments: -L 15 --no-unal
```

## 6. 下一步建议（给用户）
- 物种覆盖缺口 top 3：`Saccharomyces cerevisiae`（normalized=`saccharomyces cerevisiae`，sample=650, study=24）
- 物种覆盖缺口 top 3：`Danio rerio`（normalized=`danio rerio`，sample=430, study=2）
- 物种覆盖缺口 top 3：`Escherichia coli`（normalized=`escherichia coli`，sample=103, study=6）
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE53693 / Danio rerio`，Ribo-Seq=254，RNA-Seq=132，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE67387 / Saccharomyces cerevisiae`，Ribo-Seq=57，RNA-Seq=24，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE108778 / Saccharomyces cerevisiae`，Ribo-Seq=52，RNA-Seq=72，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE34082 / Saccharomyces cerevisiae`，Ribo-Seq=37，RNA-Seq=33，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`SRP133508 / Zea mays`，Ribo-Seq=37，RNA-Seq=15，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE125038 / Saccharomyces cerevisiae`，Ribo-Seq=28，RNA-Seq=28，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE74197 / Staphylococcus aureus`，Ribo-Seq=28，RNA-Seq=26，备注=`not in references.yaml`
- 受阻塞且 Ribo-Seq 负载较高的 study：`GSE34743 / Danio rerio`，Ribo-Seq=24，RNA-Seq=20，备注=`not in references.yaml`
- 家蚕 / 蜘蛛相关备注：当前 `metadata.csv` 里未检出 `Bombyx`、`spider`、`Latrodectus`、`Trichonephila` 等关键字，因此本轮 top 缺口里没有这两类物种。
- smoke 已通过，下一轮可以优先做 batch study 级 YAML 生成或继续补 references 覆盖；暂时不需要改 sqlite schema。
