#!/usr/bin/env python3
"""Create Research Roadmap page in Notion with evolution chains."""
from notion_api import NotionAPI


def build_paper_toggle(api, title, items):
    """Build a toggle block for a paper with bullet details."""
    children = []
    for key, value in items:
        children.append(api.bullet(value, bold_prefix=f"{key}: "))
    return api.toggle(title, children)


def build_line1_blocks(api):
    """Line 1: Body Models."""
    blocks = [
        api.heading(1, "Line 1: 体表示模型 (Body Models)"),
        api.callout(
            "核心趋势: 从PCA线性模型(SCAPE) → 顶点级线性蒙皮(SMPL) → 神经隐式表示(SDF) → 混合模型(VolumetricSMPL)。"
            "SMPL统治10年的核心原因是与图形管线的兼容性(LBS)，但物理仿真需要SDF表示。",
            "🧬"
        ),
        api.paragraph("SCAPE → SMPL → MANO/FLAME → SMPL-X → STAR → Neural Implicit → VolumetricSMPL", bold=True),
        build_paper_toggle(api, "📄 SCAPE (Anguelov et al., 2005) — 首个参数化人体", [
            ("方法", "三角形变形矩阵 + PCA on body scans，将体型和姿态变形解耦"),
            ("局限", "三角形表示不兼容图形引擎，需要最小二乘拼接，速度慢"),
            ("结果", "首次从参数生成逼真人体形变，但未被工业界采纳"),
        ]),
        build_paper_toggle(api, "📄 SMPL (Loper et al., 2015) ⭐ = SCAPE + 顶点级LBS + learned blend shapes", [
            ("核心改进", "用顶点位移替代三角形变形 → 40x加速，兼容所有图形引擎"),
            ("技术细节", "6890顶点, 23关节, 72姿态参数+10体型参数, 线性混合蒙皮(LBS)"),
            ("为什么成功", "简单、可微分、兼容图形管线 → 成为事实标准至今"),
            ("局限", "只有躯干，没有手指和面部表情"),
        ]),
        build_paper_toggle(api, "📄 MANO (Romero et al., 2017) = SMPL框架 → 手部", [
            ("核心改进", "将SMPL的LBS框架应用于手部: 778顶点, 15关节"),
            ("意义", "填补了SMPL没有手部细节的空白"),
        ]),
        build_paper_toggle(api, "📄 FLAME (Li et al., 2017) = SMPL框架 → 面部", [
            ("核心改进", "将SMPL框架应用于面部: 5023顶点, 50维表情空间"),
            ("意义", "填补了SMPL没有面部表情的空白"),
        ]),
        build_paper_toggle(api, "📄 SMPL-X (Pavlakos et al., CVPR 2019) = SMPL + MANO + FLAME 统一", [
            ("核心改进", "首个统一全身+手+脸的参数化模型: 10475顶点, 54关节"),
            ("技术细节", "SMPLify-X层次化优化: 先粗后细, 8x加速"),
            ("意义", "使得从单张图片恢复全身表达成为可能"),
        ]),
        build_paper_toggle(api, "📄 STAR (Osman et al., ECCV 2020) = SMPL + 稀疏化", [
            ("核心改进", "每个关节只影响局部mesh → 参数量减80%"),
            ("结果", "泛化误差3.1mm→2.8mm, 14000扫描训练(vs SMPL的1700)"),
        ]),
        build_paper_toggle(api, "📄 VolumetricSMPL (Mihajlovic et al., ICCV 2025) = SMPL-X + 神经SDF", [
            ("核心改进", "在SMPL基础上加神经SDF → 可微碰撞/接触查询"),
            ("为什么重要", "mesh表示无法高效做碰撞检测，物理仿真必须用SDF"),
            ("结果", "比COAP快10x, 内存省6x, 即插即用扩展SMPL"),
        ]),
    ]
    return blocks


def build_line2_blocks(api):
    """Line 2: HPE → Mesh Recovery."""
    blocks = [
        api.heading(1, "Line 2: 姿态估计 → 网格重建 (HPE → Mesh Recovery)"),
        api.callout(
            "核心突破: HMR (2018) 将SMPL嵌入端到端网络，用重投影损失+对抗训练绕开3D标签稀缺问题。"
            "此后所有改进都是在HMR框架上迭代。从HMR到TokenHMR (2024)，PA-MPJPE从70mm降到48mm。",
            "👁️"
        ),
        api.paragraph("2D HPE → 3D Lifting → HMR → SPIN → PyMAF → CLIFF → HMR 2.0 → TokenHMR", bold=True),
        build_paper_toggle(api, "📄 HMR (Kanazawa et al., CVPR 2018) ⭐ 里程碑：首次端到端 image→SMPL", [
            ("核心创新", "重投影损失(只需2D标注) + 对抗判别器(约束pose在人体流形上)"),
            ("为什么重要", "突破性解决了3D mesh恢复需要大量3D标签的难题"),
            ("技术细节", "ResNet50 → FC → 10 shape + 72 pose + 3 camera params"),
            ("局限", "纯回归精度有限, PA-MPJPE ~70mm"),
        ]),
        build_paper_toggle(api, "📄 SPIN (Kolotouros et al., ICCV 2019) = HMR + 训练时优化循环", [
            ("核心改进", "训练时交替: 网络回归初始化 → SMPLify优化 → 优化结果作为监督"),
            ("结果", "PA-MPJPE: 70mm → 59mm"),
        ]),
        build_paper_toggle(api, "📄 PyMAF (Zhang et al., ICCV 2021) = SPIN + mesh对齐特征反馈", [
            ("核心改进", "推理时迭代: 投影mesh到图像 → 提取mesh位置特征 → 修正参数"),
        ]),
        build_paper_toggle(api, "📄 CLIFF (Li et al., ECCV 2022) = PyMAF + 全局位置信息", [
            ("核心改进", "保留全帧上下文(裁剪丢失位置) → 正确预测全局旋转"),
            ("结果", "AGORA排行榜第一"),
        ]),
        build_paper_toggle(api, "📄 HMR 2.0 (Goel et al., ICCV 2023) = CLIFF + ViT backbone", [
            ("核心改进", "ViT全局自注意力替代ResNet → 极端姿态显著提升"),
            ("结果", "PA-MPJPE ~50mm"),
        ]),
        build_paper_toggle(api, "📄 TokenHMR (Dwivedi et al., CVPR 2024) = HMR2.0 + 离散pose token化", [
            ("核心改进", "将pose空间离散为token(分类替代回归) → 首次同时兼顾2D对齐和3D准确"),
            ("结果", "PA-MPJPE ~48mm, 两个指标同时最优"),
        ]),
    ]
    return blocks


def build_line3_blocks(api):
    """Line 3: Motion & Physics."""
    blocks = [
        api.heading(1, "Line 3: 运动生成 & 物理仿真 (Motion & Physics)"),
        api.callout(
            "两条路线正在融合: 数据驱动扩散模型(多样性+文本可控) + 物理仿真(物理正确性)。"
            "PDP (2024) 是目前融合最成功的工作。纯运动学方法'看起来对但物理上错'，"
            "纯物理方法'物理上对但不够多样'。",
            "⚡"
        ),
        api.heading(2, "3a. 物理控制链: DeepMimic → AMP → ASE → PULSE"),
        build_paper_toggle(api, "📄 DeepMimic (Peng et al., SIGGRAPH 2018) ⭐ RL+物理仿真模仿运动", [
            ("核心创新", "首次用深度RL+物理模拟实现运动模仿(翻跟头等高难度动作)"),
            ("局限", "需要手工选择参考运动片段"),
        ]),
        build_paper_toggle(api, "📄 AMP (Peng et al., SIGGRAPH 2021) = DeepMimic + 对抗运动先验", [
            ("核心改进", "对抗判别器从非结构化mocap学习运动先验 → 无需手选片段"),
        ]),
        build_paper_toggle(api, "📄 ASE (Peng et al., SIGGRAPH 2022) = AMP + 可复用技能嵌入", [
            ("核心改进", "低维技能嵌入空间 → 预训练后可迁移到新任务"),
        ]),
        build_paper_toggle(api, "📄 PULSE (Luo et al., ICLR 2024 Spotlight) = ASE进化 + 32维通用表征", [
            ("核心改进", "信息瓶颈蒸馏 → 32维潜空间覆盖99.8% AMASS数据"),
            ("意义", "运动控制的foundation model"),
        ]),
        api.heading(2, "3b. 生成运动链: MDM → MLD → MotionGPT"),
        build_paper_toggle(api, "📄 MDM (Tevet et al., ICLR 2023) ⭐ 首个运动扩散模型", [
            ("核心创新", "Transformer-based扩散, 预测sample本身(非噪声) → 可加几何损失"),
            ("结果", "人类42%时间偏好生成运动而非真实运动"),
        ]),
        build_paper_toggle(api, "📄 MLD (Chen et al., CVPR 2023) = MDM + 潜空间扩散", [
            ("核心改进", "在VAE潜空间做扩散 → 100x加速, 质量持平"),
        ]),
        api.heading(2, "3c. 融合前沿: 扩散 + 物理"),
        build_paper_toggle(api, "📄 PDP (Xie et al., SIGGRAPH Asia 2024) = 扩散策略 + 物理RL", [
            ("核心创新", "'噪声状态+干净动作'训练策略 → 鲁棒物理控制"),
            ("结果", "OOD物理扰动96.3%成功率, 首次物理可信的文本到运动"),
            ("为什么重要", "数据驱动(多样性) + 物理仿真(正确性) 的最佳融合"),
        ]),
    ]
    return blocks


def build_convergence_blocks(api):
    """Cross-line connections."""
    blocks = [
        api.divider(),
        api.heading(1, "三线交汇与未来方向"),
        api.callout(
            "SMPL是三条线的交汇核心 — 它同时是表征标准(Line1)、感知输出格式(Line2)、运动数据表示(Line3)。\n\n"
            "最大的gap: 从单目视频→SMPL-X mesh→物理可信的全身运动(含手指+表情)，"
            "目前没有端到端方案。PhysHMR做了body但没做hands/face；TokenHMR做了mesh但没做physics；"
            "PDP做了physics但没从视频输入。这个gap可能就是下一步的研究机会。",
            "🎯"
        ),
    ]
    return blocks


def main():
    api = NotionAPI()

    # Get parent page ID from database
    db = api.get_database()
    parent_id = db["parent"]["page_id"]
    print(f"Parent page: {parent_id}")

    # Build all blocks
    all_blocks = []
    all_blocks.append(api.callout(
        "三条互相关联的研究脉络: 人体表征模型 → 姿态估计/网格重建 → 运动生成/物理仿真。"
        "每个节点展示方法演进链: A → B = A + 创新点 → C = B + 创新点。",
        "🗺️"
    ))
    all_blocks.append(api.divider())
    all_blocks.extend(build_line1_blocks(api))
    all_blocks.append(api.divider())
    all_blocks.extend(build_line2_blocks(api))
    all_blocks.append(api.divider())
    all_blocks.extend(build_line3_blocks(api))
    all_blocks.extend(build_convergence_blocks(api))

    # Create the roadmap page (first 100 blocks)
    page = api.create_subpage(
        parent_id,
        "Research Roadmap: 3D Human Body & Motion (研究脉络)",
        all_blocks[:100]
    )
    page_id = page["id"]
    print(f"Created roadmap page: {page_id}")

    # Append remaining blocks if any
    if len(all_blocks) > 100:
        api.append_blocks(page_id, all_blocks[100:])
        print(f"Appended {len(all_blocks) - 100} additional blocks")

    print(f"Done! Total {len(all_blocks)} blocks")


if __name__ == "__main__":
    main()
