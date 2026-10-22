# 参考文献核对状态表（REFERENCE CHECK LOG）

核对日期：2026-10-22。核对方式：作者—年内部一致性自动比对 + 对近年/带 DOI 文献按题名与 DOI 定位来源页面核对书目元数据。

**核对范围声明：本轮只核书目元数据（题名、作者、年、刊、卷期/文章号、DOI）与正文作者—年引用一致性，未逐篇读取并验证全文。"已核"不等于引用内容、参数或结论依据已全部核实；投稿前对最终文献表再做一次出版社页面抽查。**

核验等级分两类：**[官方]** = 出版社官网、官方机构库或官方 PDF；**[书目]** = 第三方书目数据库或引用记录（作者/DOI 匹配，卷期细节投稿前回出版社页复核）。未标注「已核」的条目不标完成；经典无 DOI 文献仅要求内部作者—年一致。

## 一、已核对书目元数据

### A. 出版社 / 官方机构库或官方 PDF（[官方]）

| 文献条目（表内写法） | 核验结论 | 来源 |
|---|---|---|
| Liu, F., Ren, C., Chen, Y. (2024), J. Flood Risk Manag. 17(2):e12979, DOI 10.1111/jfr3.12979 | 题名、DOI、2024 一致 | [官方] Wiley Online Library |
| Tang, Y. et al. (2022), Water 14(21):3409, DOI 10.3390/w14213409 | 题名、作者首姓、卷期文章号一致 | [官方] MDPI 官方 PDF |
| Shirvani, M., Kesserwani, G. (2021), NHESS 21:3175–3198 | 题名、年、卷页一致（官方为 21(10)） | [官方] NHESS 官方 / White Rose |
| Wang, L. et al. (2024), Front. Comput. Sci. 18(6):186345, DOI 10.1007/s11704-024-40231-1 | 题名、卷期文章号、DOI 一致 | [官方] ACM DL / arXiv |
| Park, D. et al. (2026), Appl. Sci. 16(18):8952, DOI 10.3390/app16188952 | 题名、卷期文章号、DOI 一致 | [官方] MDPI 官方版本说明页 |
| Zhu, J., Dang, P., Cao, Y., et al. (2024), IJGIS 38(4):603–625, DOI 10.1080/13658816.2024.2306167 | 首作者为 Jun Zhu（非 Cao），前三位与正文 Zhu et al. (2024) 正确 | [官方] T&F 出版页 |
| Wang, Y., Cai, Z., Chu, S., et al. (2026), Frontiers in Water 8:1777013, DOI 10.3389/frwa.2026.1777013 | 已由 Wang X. 更正为 Yan Wang；完整作者 Yan Wang, Zhao Cai, Shaozhi Chu, Peng Liu, Hongwei Liu, Jin Lin, Li Tang；正文 Wang et al. (2026) 姓不变 | [官方] Frontiers 官方 PDF |
| Li, X., Guo, C., Chen, J., et al. (2026), J. Hydrology 672:135395, DOI 10.1016/j.jhydrol.2026.135395 | 作者 Xintong Li, Chenglin Guo, Jie Chen, Yufei Qin, Jun Zhang, Nikolai W.F. Bode, Weiguo Song；卷 672/文章号 135395，DOI 已补 | [官方] Bristol 机构库 |
| Li, W., Ran, Q., Dang, P., et al. (2026), 测绘学报 55(1):154–168, DOI 10.11947/j.AGCS.2026.20250271 | 作者 Weilian LI, Qingqing RAN, Pei DANG, Jun ZHU, Qing ZHU, Heng ZHANG；首三位、卷期页、DOI | [官方] 中文出版页 |

### B. 第三方书目记录（[书目]，投稿前回出版社页复核）

| 文献条目（表内写法） | 核验结论 | 来源 |
|---|---|---|
| Yang, X.X. et al. (2025), Physica A 678:130924, DOI 10.1016/j.physa.2025.130924 | 题名、作者（Xiaoxia Yang, Jiahui Wan, Yongxing Li, et al.）、DOI 匹配 | [书目] ORCID / Semantic Scholar |
| Yang, S. et al. (2026), RESS 269:112056, DOI 10.1016/j.ress.2025.112056 | 题名、首作者 S. Yang、DOI 匹配 | [书目] BibSonomy 书目记录 |
| Hu, M., Tang, J., He, G. (2022), 深圳大学学报理工版 39(2):159–167, DOI 10.3724/SP.J.1249.2022.02159 | 作者胡明伟, 汤静妍, 何国庆；题名《地铁车站水侵应急疏散仿真研究》、首三位、DOI 匹配 | [书目] 第三方引用记录 |
| Wang, Z., Wang, Z., Huang, H. (2025), 灾害学 40(4):152–157, DOI 10.3969/j.issn.1000-811X.2025.04.020 | 作者 WANG Zhe, WANG Zehan, HUANG Haichen；题名《基于实时知识库的洪涝应急决策智能问答模型研究》、首三位、DOI 匹配 | [书目] 万方 |

## 二、内部一致性（自动比对）

- 正文所有作者—年引用均可在文献表找到对应条目；脚本初报的两处「缺失」（Penning-Rowsell 2008、State Council 2022）为抽取误判，原文条目（Jonkman & Penning-Rowsell 2008；郑州 7·20 调查报告 2022）均在表内，非断引。
- 表内条目与正文引用方向无矛盾；经典无 DOI 文献（Helbing、Breiman、Chen&Guestrin、Kahneman&Tversky、Simon、Rogers、Ajzen、Latané、Lindell&Perry、Terpstra、Wachinger、Sorensen、Dash&Gladwin、Nonaka、Gruber、Park 2023、Sumers、Kazil、Argyle、Aher、Horton、Xia、Zhu Z.F. 等）作者—年内部一致，投稿前按目标期刊体例统一卷期页即可。

## 三、投稿前待办（不阻塞本轮）

1. B 类 [书目] 4 条回出版社官网复核卷期页与完整作者名单。
2. 经典无 DOI 文献按 AEI 目标期刊体例统一卷期页与著录格式。
3. 标准类 GB 50157-2013、GB/T 33668-2017 按目标期刊标准著录格式补编号年份。
4. 投稿前对最终文献列表再做一次出版社页面抽查（尤其在线优先、卷期变更项），并按需核对引用内容与原文。
