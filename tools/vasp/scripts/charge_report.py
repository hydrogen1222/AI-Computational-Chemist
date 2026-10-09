#!/usr/bin/env python3
"""Generate source-traceable Chinese atomic charge reports from existing CSVs.

Bader, Chargemol DDEC6, Chargemol noniterative Hirshfeld/CM5 and Multiwfn.
No DFT or analysis binaries are executed. Existing CSVs are not modified.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import math
from pathlib import Path
import sys

FILES = {
    "bader": ("bader_cases.csv", "bader_elements.csv", "bader_atoms.csv"),
    "ddec6": ("ddec6_cases.csv", "ddec6_elements.csv", "ddec6_atoms.csv", "ddec6_bond_types.csv"),
    "hirshfeld": ("hirshfeld_cases.csv", "hirshfeld_elements.csv", "hirshfeld_atoms.csv"),
    "multiwfn": ("multiwfn_qc.csv", "multiwfn_elements.csv", "multiwfn_atoms.csv"),
}
REPORTS = {
    "bader": "bader_summary.md",
    "ddec6": "ddec6_report_cn.md",
    "hirshfeld": "hirshfeld_report_cn.md",
    "multiwfn": "multiwfn_report_cn.md",
}


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def safe(value):
    return str(value if value is not None else "").replace("|", r"\|").replace("\r", " ").replace("\n", " ").strip()


def fmt(value, decimals=4, signed=False):
    if value is None or str(value).strip() == "":
        return "—"
    if str(value).strip() in {"NOT_CHECKED", "NOT_VERIFIED"}:
        return "未检查"
    try:
        v=float(value)
    except (ValueError,TypeError):
        return safe(value)
    if not math.isfinite(v):
        return "非有限值，不可引用"
    return f"{v:+.{decimals}f}" if signed else f"{v:.{decimals}f}"


def table(headers, rows):
    lines=["| "+" | ".join(safe(x) for x in headers)+" |",
           "| "+" | ".join("---" for _ in headers)+" |"]
    lines.extend("| "+" | ".join(safe(x) for x in row)+" |" for row in rows)
    return "\n".join(lines)+"\n\n"


def by_case(records):
    indexed=defaultdict(list)
    for row in records:
        indexed[row["case"]].append(row)
    return indexed


def summary_sentence(rows, key, method):
    pieces=[]
    for row in rows:
        try:
            q=float(row[key])
        except (KeyError,ValueError,TypeError):
            continue
        if not math.isfinite(q):continue
        state="电子亏损" if q>1e-6 else "电子富集" if q<-1e-6 else "接近零"
        pieces.append(f"{row['element']} 的平均净电荷为 {q:+.4f} e（{state}）")
    if not pieces:
        return f"{method} 未产生可引用的元素平均电荷。"
    return "；".join(pieces)+"。这一解释仅针对本次电荷划分，不等同于形式氧化态，也不能独自证明反应或电荷转移路径。"


def header(title, method, inputs, count):
    sources="、".join(inputs)
    return (f"# {title}｜原子电荷汇报稿\n\n"
            f"**计算方法：** {method}。\n\n"
            f"**数据来源：** {sources}（{count} 个案例）。报告由已有 CSV 生成，未重新计算电子密度。\n\n"
            "**符号与边界：** 净原子电荷 q 的单位为 e；正值表示按该方法分配后电子亏损，"
            "负值表示电子富集。原子部分电荷不是形式氧化态；"
            "不同方法和芯价参考密度下的数值不应无条件混用。\n\n"
            "**阅读顺序：** 先看每例状态和电荷核对，再看可供 PPT 使用的文字，"
            "最后是完整元素及原子列表。方法检查未通过时不生成定量结论。\n\n")


def render_bader(items):
    cases,elements,atoms=items
    byel,byatom=by_case(elements),by_case(atoms)
    text=header("AIM / Bader", "Bader 分区；q = POTCAR ZVAL − Bader 区域价电子数。"
        "若执行计算，以 AECCAR0+AECCAR2 构建分区参考密度",
        FILES["bader"],len(cases))
    for c in cases:
        case=c["case"]
        text+=f"## 案例：{safe(case)}\n\n**状态：** {safe(c['status'])}；{safe(c.get('detail',''))}。\n\n"
        if c["status"]!="OK":
            text+="**本例没有合格电荷，不能汇报数值。**\n\n";continue
        er,ar=byel[case],byatom[case]
        if not er or not ar:
            text+="**本例缺少有效元素/原子数据，不能汇报数值。**\n\n";continue
        qsum=sum(float(a["net_charge_e"]) for a in ar)
        target=c.get("expected_net_charge_e","")
        delta=c.get("charge_balance_error_e","NOT_CHECKED")
        text+=f"**晶胞电荷核对：** Σq = {qsum:+.6f} e；期望净电荷 {fmt(target,6,True)} e；"
        if str(delta).strip() not in {"","NOT_CHECKED"}:
            text+=f"差值 {fmt(delta,6,True)} e（已按给定目标检查）。\n\n"
        else:
            text+="**未验证**（未提供期望净电荷；即使 Σq 接近零也不能标为通过）。\n\n"
        text+="**可以放进 PPT 的结果描述：** "+summary_sentence(er,"mean_q_e","Bader")+"\n\n"
        text+="**全部元素统计：**\n\n"+table(
            ["元素","原子数","平均 q / e","最小 q / e","最大 q / e","跨度 / e"],
            [[r["element"],r["count"],fmt(r["mean_q_e"],4,True),
              fmt(r["min_q_e"],4,True),fmt(r["max_q_e"],4,True),
              fmt(r["spread_e"],4)] for r in er])
        text+="**逐原子电荷（全部）：**\n\n"+table(
            ["编号","元素","ZVAL / e","区域价电子数","q / e"],
            [[r["atom_index"],r["element"],fmt(r["zval"]),fmt(r["bader_electrons"],5),
              fmt(r["net_charge_e"],5,True)] for r in ar])
        text+=f"**原始 Bader ACF 路径：** {safe(c.get('acf_path',''))}。\n\n"
    text+=("## 解读限制\n\n"
           "元素均值不能代替不等价晶位的逐原子分析。需核验 VASP 密度网格、"
           "参考密度、PAW ZVAL、静态结构及跨材料计算设置一致性。"
           "不要把局部电荷数值单独作为氧化态或机理证明。\n")
    return text


def render_ddec6(items):
    cases,elements,atoms,bondtypes=items
    el,at,bo=by_case(elements),by_case(atoms),by_case(bondtypes)
    text=header("Chargemol DDEC6 原子电荷与键级",
        "DDEC6 净电荷、原子键级和 SBO、跨晶胞成对 BO；"
        "BO 和 SBO 为无量纲，均不等于 ICOHP 或整数 Lewis 键级",
        FILES["ddec6"],len(cases))
    for c in cases:
        case=c["case"]
        text+=f"## 案例：{safe(case)}\n\n**状态：** {safe(c['status'])}；{safe(c.get('detail',''))}。\n\n"
        if c["status"]!="OK":
            text+="**该例分析失败，不引用 DDEC6 电荷或键级。**\n\n";continue
        er,ar,br=el[case],at[case],bo[case]
        if not er or not ar:
            text+="**缺少有效原子或元素数据。**\n\n";continue
        delta=c.get("charge_balance_error_e","NOT_CHECKED")
        text+=f"**电荷核对：** Σq = {fmt(c.get('sum_ddec6_q_e'),6,True)} e，"
        text+=f"与输入净电荷的偏差 {fmt(delta,6,True)} e。"
        text+=("未给定净电荷目标，守恒未检查。" if str(delta) in {"","NOT_CHECKED"}
               else "已按提供的电荷目标检查。")
        text+=f"**键级检查：** {safe(c.get('bond_qc_status','NOT_CHECKED'))}；"
        text+=f"contact-exchange 指标 {fmt(c.get('contact_exchange_error_e'),6)} e；"
        text+="缺少日志指标不能解释为通过。\n\n"
        text+="**可以放进 PPT 的结果描述：** "+summary_sentence(er,"mean_charge_e","DDEC6")+"\n\n"
        text+="**全部元素的 q 与 SBO：**\n\n"+table(
            ["元素","原子数","平均 q / e","q 最小～最大 / e","平均 SBO","SBO 最小～最大"],
            [[r["element"],r["n_atoms"],fmt(r["mean_charge_e"],4,True),
              fmt(r["min_charge_e"],4,True)+" ～ "+fmt(r["max_charge_e"],4,True),
              fmt(r["mean_sbo"],4),fmt(r["min_sbo"],4)+" ～ "+fmt(r["max_sbo"],4)] for r in er])
        text+="**全部 Chargemol 已打印的键型：**\n\n"+table(
            ["元素对","不重复周期键条数","平均 BO","最小～最大 BO"],
            [[r["element_pair"],r["n_periodic_bonds"],fmt(r["mean_bond_order"],5),
              fmt(r["min_bond_order"],5)+" ～ "+fmt(r["max_bond_order"],5)] for r in br])
        text+="**全部原子电荷与键级：**\n\n"+table(
            ["编号","元素","q / e","SBO","已打印 SBO 贡献","未打印残差"],
            [[r["atom_index_1based"],r["element"],fmt(r["ddec6_net_charge_e"],5,True),
              fmt(r["sum_bond_orders"],5),fmt(r.get("sbo_from_printed_pairs"),5),
              fmt(r.get("sbo_unprinted_remainder"),5)] for r in ar])
        text+=f"**Chargemol 原始输出路径：** {safe(c.get('chargemol_dir',''))}。\n\n"
    text+=("## 科学注意事项\n\n"
           "周期镜像自身键对于其原子的 SBO 可以计入两次；未打印的微弱键贡献"
           "使 SBO 不必恰等于输出逐键 BO 的和。平均 BO 的范围是 min–max，"
           "不是不确定度。如果 BO 内部一致性检查失败，不能引用相应 SBO/键级。\n")
    return text


def render_hirshfeld(items):
    cases,elements,atoms=items
    el,at=by_case(elements),by_case(atoms)
    text=header("Chargemol 普通 Hirshfeld 与 CM5",
        "读取 Chargemol 初始非迭代 Hirshfeld 分区和 CM5；不包含 Hirshfeld-I",
        FILES["hirshfeld"],len(cases))
    for c in cases:
        case=c["case"]
        text+=f"## 案例：{safe(case)}\n\n**状态：** {safe(c['status'])}；{safe(c.get('detail',''))}。\n\n"
        if c["status"]!="OK":
            text+="**该案例无合格电荷。**\n\n";continue
        er,ar=el[case],at[case]
        if not er or not ar:
            text+="**缺少原子/元素数据。**\n\n";continue
        text+="**可以放进 PPT 的结果描述：** "+summary_sentence(er,"hirshfeld_mean_e","普通 Hirshfeld")+"\n\n"
        text+=f"**晶胞电荷：** Hirshfeld Σq = {fmt(c.get('hirshfeld_charge_sum_e'),6,True)} e；"
        text+=f"CM5 Σq = {fmt(c.get('cm5_charge_sum_e'),6,True)} e；"
        text+=f"目标总电荷 {fmt(c.get('expected_net_charge_e'),6,True)} e。"
        text+="没有指定目标时不宣称守恒通过。\n\n"
        text+="**全部元素：**\n\n"+table(
            ["元素","数目","Hirshfeld 平均 / e","H 最小～最大 / e","CM5 平均 / e","DDEC6 平均 / e"],
            [[r["element"],r["count"],fmt(r["hirshfeld_mean_e"],5,True),
              fmt(r["hirshfeld_min_e"],5,True)+" ～ "+fmt(r["hirshfeld_max_e"],5,True),
              fmt(r.get("cm5_mean_e"),5,True),fmt(r.get("ddec6_mean_e"),5,True)] for r in er])
        text+="**全部原子：**\n\n"+table(
            ["编号","元素","Hirshfeld / e","CM5 / e","DDEC6 / e"],
            [[r["atom_index_1based"],r["element"],fmt(r["hirshfeld_net_charge_e"],6,True),
              fmt(r.get("cm5_net_charge_e"),6,True),fmt(r.get("ddec6_net_charge_e"),6,True)] for r in ar])
        text+=f"**来源日志：** {safe(c.get('source_log',''))}。\n\n"
    text+=("## 与 Multiwfn 比较的边界\n\n"
           "Chargemol 和 Multiwfn 虽都使用普通 Hirshfeld/CM5 名称，"
           "但可能采用不同体系电子密度、自由原子参考密度、芯价处理、积分网格。"
           "**这种差异可以是正常的方法依赖性，不能在未做受控测试时断言差异完全由某一因素造成。**"
           "CM5 修正依赖 Hirshfeld 基线，不能跨软件混搭。\n")
    return text


def render_multiwfn(items):
    qc,elements,atoms=items
    byqc,el,at=by_case(qc),by_case(elements),by_case(atoms)
    text=header("Multiwfn 周期性 Hirshfeld / CM5 与 Chargemol 对照",
        "Multiwfn 普通 Hirshfeld、CM5、Hirshfeld-I；"
        "读取同案例 Chargemol 非迭代 Hirshfeld/CM5 与 DDEC6 作为独立对照",
        FILES["multiwfn"],len(byqc))
    methods={"hirshfeld":"普通 Hirshfeld","cm5":"CM5","hirshfeld_i":"Hirshfeld-I"}
    for case in sorted(byqc):
        statuses=byqc[case]
        passed={r["method"] for r in statuses if r["status"]=="OK"}
        text+=f"## 案例：{safe(case)}\n\n**逐方法质量状态：**\n\n"+table(
            ["方法","解析状态","Σq / e","目标 / e","日志提示"],
            [[methods.get(r["method"],r["method"]),r["status"],
              fmt(r.get("charge_sum_e"),6,True),fmt(r.get("expected_charge_e"),6,True),
              r.get("detail","")] for r in statuses])
        er=[r for r in el[case] if r["method"] in passed]
        ar=at[case]
        if not er or not ar:
            text+="**本例无可用原子电荷，不生成数值结论。**\n\n";continue
        text+="**可以放进 PPT 的结果描述：**\n\n"
        for method in ("hirshfeld","cm5"):
            current=[r for r in er if r["method"]==method]
            if current:
                text+=f"**{methods[method]}：** "+summary_sentence(current,"mean_q_e",method)+"\n\n"
        if "hirshfeld_i" in passed:
            text+="**重要：Hirshfeld-I 虽已解析，但还需要逐轮收敛证据；解析成功并不代表迭代收敛，正式定量引用前必须核查。**\n\n"
        else:
            text+="**Hirshfeld-I 未取得合格结果，不报告中间迭代值。**\n\n"
        text+="**全部已成功解析的元素统计：**\n\n"+table(
            ["方法","元素","原子数","平均 q / e","最小～最大 / e"],
            [[methods.get(r["method"],r["method"]),r["element"],r["n_atoms"],
              fmt(r["mean_q_e"],5,True),
              fmt(r["min_q_e"],5,True)+" ～ "+fmt(r["max_q_e"],5,True)] for r in er])
        def cell(r,method,key):
            return fmt(r.get(key),6,True) if method in passed else "不可引用"
        text+="**全部逐原子对照：**\n\n"+table(
            ["编号","元素","Multiwfn H","Multiwfn CM5","Multiwfn H-I（待验收）",
             "Chargemol H","Chargemol CM5","DDEC6"],
            [[r["atom_1based"],r["element"],
              cell(r,"hirshfeld","multiwfn_hirshfeld_e"),
              cell(r,"cm5","multiwfn_cm5_e"),
              cell(r,"hirshfeld_i","multiwfn_hirshfeld_i_e"),
              fmt(r.get("chargemol_hirshfeld_e"),6,True),
              fmt(r.get("chargemol_cm5_e"),6,True),
              fmt(r.get("chargemol_ddec6_e"),6,True)] for r in ar])+"\n"
        text+=("**交叉比较解释：** 仅将同名的 H–H、CM5–CM5 作为有符号差值诊断；"
               "不同参考密度与芯价电子约定可造成数值/符号差异，不意味着其中一方一定错误。\n\n")
    text+=("## 验收边界\n\n"
           "Hirshfeld-I 必须逐轮确认收敛；缺少 S-3.rad 等参考态而终止时，"
           "最后一轮的数字无效。DDEC6 与 Hirshfeld-I 不是同一方法。"
           "跨体系对比需说明 Multiwfn/Chargemol 版本、电子密度及参考约定。"
           "没有网格和参考态核验，不得做过度的电荷转移机制推断。\n")
    return text


RENDER={
    "bader":render_bader,
    "ddec6":render_ddec6,
    "hirshfeld":render_hirshfeld,
    "multiwfn":render_multiwfn,
}


def generate(folder,method):
    if method not in FILES:raise ValueError(f"unknown method {method}")
    inputs=[folder/name for name in FILES[method]]
    missing=[p.name for p in inputs if not p.is_file()]
    if missing:raise FileNotFoundError("缺少 CSV：" + ", ".join(missing))
    data=[csv_rows(p) for p in inputs]
    if not data[0]:raise ValueError("没有案例/QC 记录")
    output=folder/REPORTS[method]
    output.write_text(RENDER[method](data),encoding="utf-8")
    return output


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path,help="Existing postprocess_summary folder")
    p.add_argument("--methods",nargs="+",choices=list(FILES),default=list(FILES))
    p.add_argument("--only-present",action="store_true",help="Skip missing method families")
    options=p.parse_args(argv)
    folder=options.folder.expanduser().resolve()
    if not folder.is_dir():p.error(f"summary directory missing: {folder}")
    errors=0
    for method in options.methods:
        if options.only_present and not (folder/FILES[method][0]).is_file():
            print(f"SKIP {method}: 无案例 CSV")
            continue
        try:
            dest=generate(folder,method)
            print(f"REPORT {method}: {dest}")
        except (OSError,ValueError,KeyError) as exc:
            print(f"ERROR {method}: {exc}",file=sys.stderr)
            errors+=1
    return 1 if errors else 0


if __name__=="__main__":
    sys.exit(main())
