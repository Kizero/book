from __future__ import annotations

import re
from pathlib import Path


SOURCE = Path("/Users/houguanqun/Downloads/《谈判力》读书笔记.md")
OUT_DIR = Path("/Users/houguanqun/Downloads/book/book/谈判力播客")
MD_OUT = OUT_DIR / "《谈判力》中文播客口播稿.md"
TXT_OUT = OUT_DIR / "《谈判力》中文播客纯文本.txt"


def extract(lines: list[str], start: int, end: int) -> str:
    """Extract one-based inclusive source lines without changing their wording."""
    return "\n".join(lines[start - 1 : end]).strip()


def normalize_markdown_for_speech(text: str) -> str:
    text = re.sub(
        r"^> 单人中文播客口播稿。.*$",
        "",
        text,
        flags=re.MULTILINE,
    )
    # Items that are useful in the written transcript but should not be read aloud.
    text = re.sub(
        r"\s*\[(?:Demonstrations, Hostility Greet Waldheim in Iran|Waldheim's Mission To Iran Ends With No Sign of Progress|Iran hostage rescue mission ends in disaster \| April 24, 1980 \| HISTORY|Iran hostage crisis - Wikipedia)\]\(https?://[^)]+\)",
        "",
        text,
    )
    text = re.sub(r"!\[[^]]*\]\([^)]+\)", "原文此处附有图片。", text)
    text = re.sub(r"\[([^]]+)\]\(https?://[^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)

    # Spoken equivalents for the few visual-only Markdown structures.
    text = text.replace(
        "| 有产阶级 | 无产阶级 |\n| --- | --- |\n"
        "| 解释器自然趋同 | 需要人为统一解释器——提供一个统一的\"元解释器\"（阶级分析框架） |\n"
        "| 市场自动协调利益（市场如丛林，带有右翼属性） | 需要政党/工会来组织——创造共同实践的空间（工会、政党） |\n"
        "| 通过资本网络连接 | 需要理论武装和宣传——在共同行动中校准彼此的解释器 |",
        "有产阶级这一边，解释器自然趋同；无产阶级这一边，需要人为统一解释器，提供一个统一的元解释器，也就是阶级分析框架。\n"
        "有产阶级由市场自动协调利益，市场如丛林，带有右翼属性；无产阶级需要政党和工会来组织，创造共同实践的空间。\n"
        "有产阶级通过资本网络连接；无产阶级需要理论武装和宣传，在共同行动中校准彼此的解释器。",
    )
    text = text.replace(
        "| 领袖/组织 | 有产者的应对 | 结果 |\n| --- | --- | --- |\n"
        "| 卢森堡、李卜克内西 | 暗杀 | 德国革命失败 |\n"
        "| 美国工运领袖（1920s） | 红色恐慌、FBI渗透 | 工会官僚化 |\n"
        "| 拉美左翼领袖 | CIA政变（智利阿连德等） | 军政府上台 |\n"
        "| 黑豹党 | COINTELPRO计划 | 组织瓦解 |",
        "卢森堡、李卜克内西，面对的是暗杀，结果是德国革命失败。\n"
        "美国二十世纪二十年代的工运领袖，面对的是红色恐慌和联邦调查局渗透，结果是工会官僚化。\n"
        "拉美左翼领袖，面对的是中情局政变，比如智利的阿连德，结果是军政府上台。\n"
        "黑豹党，面对的是反情报计划，结果是组织瓦解。",
    )

    # Markdown and symbols that should become natural pauses rather than spoken noise.
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```[^\n]*$", "", text, flags=re.MULTILINE)
    text = text.replace("```", "")
    text = re.sub(r"\*\*|__|~~|`", "", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.MULTILINE)
    chinese_ordinals = {"1": "第一", "2": "第二", "3": "第三", "4": "第四", "5": "第五"}
    text = re.sub(
        r"^\s*([1-5])\.\s+",
        lambda m: f"{chinese_ordinals[m.group(1)]}，",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
    text = text.replace("→", "，于是，").replace("↓", "接下来")
    text = text.replace("=", "等于").replace("+", "加上")
    text = text.replace("™", "").replace("👍🏻", "点了个赞")
    text = text.replace("diao", "屌")

    # Read common English terms in the author's intended Chinese sense.
    spoken_terms = {
        "Fundamental Attribution Error": "基本归因错误",
        "claiming value": "价值分配",
        "creating value": "价值创造",
        "Exoteric Teaching": "显白教诲",
        "Esoteric Teaching": "隐微教诲",
        "buffer": "缓冲区",
        "scapegoat": "替罪羊",
        "Ben Franklin Effect": "本杰明·富兰克林效应",
        "All in": "全押",
        "Deep State": "深层政府",
        "Iran-Contra": "伊朗康特拉事件",
        "FBI": "联邦调查局",
        "CIA": "中情局",
        "COINTELPRO": "反情报计划",
        "compromise": "妥协",
        "AI": "人工智能",
    }
    for original, spoken in spoken_terms.items():
        text = text.replace(original, spoken)

    text = text.replace("t1", "T一").replace("t2", "T二")
    text = text.replace("P11", "第十一页").replace("P27", "第二十七页")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()

    parts: list[dict[str, object]] = [
        {
            "title": "第一章：双赢的假面与超越立场的前提",
            "cue": "书一开头，从美苏核试验检查次数的争执讲起。作者认为，双方纠缠于三次还是十次，却没有进一步设计每次检查的规模和方式，于是立场遮蔽了真正的利益。我的第一反应，却是先问：所谓双赢，究竟是谁定义的？",
            "ranges": [(25, 38)],
        },
        {
            "title": "第二章：四条原则，以及信息差与权力差",
            "cue": "作者随后把原则谈判概括为四条：把人和事分开；着眼于利益，而不是立场；为共同利益创造选择方案；坚持使用客观标准。",
            "ranges": [(46, 54)],
        },
        {
            "title": "第三章：谈判者首先是人",
            "cue": "接下来，书里强调了一个看似普通、其实很容易被遗忘的事实：谈判桌对面不是一个抽象的机构，而是一个活生生的人。",
            "ranges": [(63, 84)],
        },
        {
            "title": "第四章：认知、情绪、交流，以及组织里的浑水摸鱼",
            "cue": "书里主张把关系利益和实质利益分开处理，并把人际问题拆成认知、情绪和交流三个方面。这一部分，我更关心它在真实组织里的困难。",
            "ranges": [(111, 152)],
        },
        {
            "title": "第五章：不要只看事实，要调试解释器",
            "cue": "谈到认知分歧时，书里的核心意思是：冲突不只存在于客观事实中，也存在于人们解释事实的方式中。这个说法在我看来有些极端，但它可以被翻译成一个很清楚的技术比喻。",
            "ranges": [(172, 222)],
        },
        {
            "title": "第六章：归因的三个境界",
            "cue": "在理解对方之后，还要避免用自己的恐惧推测对方的意图，也不要把人与问题重新绑死。顺着这条线，我想到归因其实有三个境界。",
            "ranges": [(251, 254)],
        },
        {
            "title": "第七章：伊朗人质危机——教学案例背后的历史",
            "cue": "书中用一次波斯语翻译造成的外交灾难说明文化误解：联合国秘书长瓦尔德海姆的发言，被翻译成了以爱管闲事者的身份，寻找有损原则的办法。但当我继续往历史深处查，这个故事远不只是一次翻译事故。",
            "ranges": [(259, 300)],
        },
        {
            "title": "第八章：私下谈判、观众成本与政治生存",
            "cue": "书里还主张减少媒体、国内观众和第三方的干扰，通过私下渠道和小规模会谈提高沟通质量。围绕这一点，我们先谈几个事实。",
            "ranges": [(305, 325)],
        },
        {
            "title": "第九章：富兰克林效应与文化认同",
            "cue": "再往下，作者谈到本杰明·富兰克林向别人借书的技巧。一个人帮了你，反而可能因此更加喜欢你。这个小技巧让我想到的，是文化认同建立时那种极快的速度。",
            "ranges": [(330, 333), (337, 338)],
            "after": "原文这里附了两张米芾草书图片。",
        },
        {
            "title": "第十章：十月惊奇与被操纵的利益认知",
            "cue": "讲到利益而不是立场时，书里再次回到戴维营协议和伊朗人质危机，并尝试站到伊朗学生领袖的位置，分析他们为什么不愿立刻释放人质。到这里，我反而想到了著名的十月惊奇阴谋论。",
            "ranges": [(387, 408)],
        },
        {
            "title": "第十一章：基本需求、常识与具身训练",
            "cue": "作者把安全感、经济利益、归属感、获得认同和主宰生活列为人的基本需求。道理朴素得像常识，但常识本身，也许就是漫长经验留下的结晶。",
            "ranges": [(422, 470)],
        },
        {
            "title": "第十二章：把馅饼做大，以及被转移到未来的成本",
            "cue": "原则谈判鼓励人们创造新的选择，把馅饼做大，而不是只争夺现成的份额。但重新回到开头的假面问题，我又多了一层认识。",
            "ranges": [(479, 488)],
        },
        {
            "title": "第十三章：卡特与把创造、决定分开",
            "cue": "书里另一个很实用的建议，是把创造方案和决定方案分开：先允许想象力展开，再进行评判和选择。这个方法和卡特时代的历史气质，在我看来有一种微妙的联系。",
            "ranges": [(507, 522)],
        },
        {
            "title": "第十四章：原则不是立场",
            "cue": "原则谈判最微妙的地方，是坚持客观标准，同时仍然愿意接受合理劝说。拿原则支持既定立场，与真正按照原则解决问题，并不是一回事。",
            "ranges": [(532, 533)],
        },
        {
            "title": "第十五章：不讲价、筛选机制与人工智能之后",
            "cue": "最后，书里谈到一个写着不讲价的商店：如果价格有公平合理的客观标准，你可以接受；如果没有，也可以离开。可我对不讲价这件事本身更感兴趣。",
            "ranges": [(543, 546)],
        },
    ]

    intro = (
        "大家好，欢迎收听这一期节目。\n\n"
        "今天想聊的是《谈判力》。这不是一期内容提要，也不是把书里的方法重新复述一遍。"
        "我更想沿着书中的案例往外走：去看双赢背后的权力，去看客观事实背后的解释器，"
        "也去看谈判者身后的国家、组织、阶级、观众和历史。\n\n"
        "书摘我会尽量略去，只保留理解后面思考所必需的背景。真正要展开的，是阅读过程中一路生长出来的东西。"
    )
    outro = (
        "以上就是这一期关于《谈判力》的阅读和岔想。它最终走得比谈判本身远得多，"
        "但也许阅读的意义就在这里：一本书提供的不是终点，而是继续追问的起点。\n\n"
        "感谢收听。"
    )

    doc: list[str] = [
        "# 《谈判力》：双赢的假面、权力与人的解释器",
        "",
        "> 单人中文播客口播稿。书中大段原文已删除；原作者的评论、推演、历史材料、比喻和个人表达完整保留。链接仅供文字稿查阅，不在音频中朗读。",
        "",
        "## 开场",
        "",
        intro,
    ]

    included_source_lines: set[int] = set()
    for part in parts:
        doc.extend(["", f"## {part['title']}", "", str(part["cue"]), ""])
        for start, end in part["ranges"]:  # type: ignore[index]
            doc.append(extract(lines, start, end))
            doc.append("")
            included_source_lines.update(range(start, end + 1))
        if part.get("after"):
            doc.append(str(part["after"]))

    doc.extend(["", "## 收束", "", outro, ""])
    markdown = "\n".join(doc)

    # Two obvious transcription/typing corrections; ideas and wording otherwise remain untouched.
    markdown = markdown.replace("海瑞与嘉庆", "海瑞与嘉靖")
    markdown = markdown.replace("中国当年的开放就史自1979年", "中国当年的开放就始自1979年")
    markdown = markdown.replace(
        "> 今年的**正仓院展，**想想就™的心里有气。。溥伟他们都™王八艹的\n\n原文这里附了两张米芾草书图片。",
        "原文这里附了两张米芾草书图片。\n\n> 今年的**正仓院展，**想想就™的心里有气。。溥伟他们都™王八艹的",
    )
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text(markdown, encoding="utf-8")
    TXT_OUT.write_text(normalize_markdown_for_speech(markdown), encoding="utf-8")

    # Guardrail: every intended author-content line must be present in the assembled script.
    expected_ranges = [
        (25, 38), (46, 54), (63, 84), (111, 152), (172, 222), (251, 254),
        (259, 300), (305, 325), (330, 333), (337, 338), (387, 408),
        (422, 470), (479, 488), (507, 522), (532, 533), (543, 546),
    ]
    expected = {n for start, end in expected_ranges for n in range(start, end + 1)}
    missing = sorted(expected - included_source_lines)
    if missing:
        raise RuntimeError(f"Author-content lines missing from podcast script: {missing}")

    print(f"Wrote {MD_OUT}")
    print(f"Wrote {TXT_OUT}")
    print(f"Preserved {len(included_source_lines)} source lines of author content")


if __name__ == "__main__":
    main()
