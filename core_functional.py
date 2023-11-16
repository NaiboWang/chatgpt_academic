# 'primary' 颜色对应 theme.py 中的 primary_hue
# 'secondary' 颜色对应 theme.py 中的 neutral_hue
# 'stop' 颜色对应 theme.py 中的 color_er
# 默认按钮颜色是 secondary
from toolbox import clear_line_break


def get_core_functions():
    return {
        "English Academic Writing Improvement": {
            # 前言
            "Prefix":   r"Below is a paragraph from an academic paper. Polish the writing to meet the academic style, " +
                        r"improve the spelling, grammar, clarity, concision and overall readability. When necessary, rewrite the whole sentence: " + "\n\n",
                        # +  r"Furthermore, list all modification and explain the reasons to do so in markdown table." + "\n\n"
            # 后语
            "Suffix":   r"",
            "Color":    r"secondary",    # 按钮颜色
        },
        "Check Grammar": {
            "Prefix":   r"""请检查以下英文句子的语法和拼写是否正确，如果有错误，首先以中文指出错误并说明如何纠正（每个错误一行），然后给出正确的英文版本；如果没有错误，就说'语法没有错误'；同时，请阅读这个句子，看看它在语义上是否正确，如果有错误，首先以中文指出错误并说明如何纠正（每个错误一行），然后给出正确的英文版本；如果没有错误，就说'语义没有错误'：""" + "\n\n",

                        # Please check whether the grammar and spelling is correct for the following sentence(s), if there are mistakes, first point out the mistakes and how to correct them in Chinese (each mistake takes one line), then give the corrected version; if no mistake, just say 'no mistake for grammar'; meanwhile, please read this sentence to see if it is semantically correct, if there are mistakes, first point out the mistakes and how to correct them in Chinese (each mistake takes one line), then give the corrected version; if no mistake, just say 'no mistake for meaning': 

                        # r"Do not try to polish the text, if no mistake is found, tell me that this paragraph is good." +
                        # r"If you find grammar or spelling mistakes, please list mistakes you find in a two-column markdown table, " +
                        # r"put the original text the first column, " +
                        # r"put the corrected text in the second column and highlight the key words you fixed.""\n"
                        # r"Example:""\n"
                        # r"Paragraph: How is you? Do you knows what is it?""\n"
                        # r"| Original sentence | Corrected sentence |""\n"
                        # r"| :--- | :--- |""\n"
                        # r"| How **is** you? | How **are** you? |""\n"
                        # r"| Do you **knows** what **is** **it**? | Do you **know** what **it** **is** ? |""\n"
                        # r"Below is a paragraph from an academic paper. "
                        # r"You need to report all grammar and spelling mistakes as the example before."
                        # + "\n\n",
            "Suffix":   r"",
        },
        "学术中译英": {
            "Prefix":   r"Please translate following sentence to English in academic style: " + "\n\n",
            "Suffix":   r"",
        },
        "中译英": {
            "Prefix":   r"翻译成英文，如果有代码就以```包围，没有就不包围：" + "\n\n",
            "Suffix":   r"",
        },
        "英译中": {
            "Prefix":   r"翻译成地道的中文：" + "\n\n",
            "Suffix":   r"",
        },
        "Rebuttal Improvement": {
            "Prefix":   r"Suggest some improvement version or strong version in rebuttal" + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write Academic Paper": {
            "Prefix": r"Please write an academic paragraph in academic style based on the following description: " + "\n```\n",
            "Suffix": "\n```\n",
        },
        "Rephrase Sentences": {
            "Prefix":   r"Rephrase the following sentences: " + "\n\n",
            "Suffix":   r"",
        },
        "Rephrase Title": {
            "Prefix":   r"Rephrase the following title: " + "\n\n",
            "Suffix":   r"",
        },
        "Expand Words to Sentences": {
            "Prefix":   r"Expand these words to whole sentences: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write Latex Code": {
            "Prefix":   r"Please write Latex code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write Python Code": {
            "Prefix":   r"Please write Python code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write JavaScript Code": {
            "Prefix":   r"Please write JavaScript code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write Linux Shell Code": {
            "Prefix":   r"Please write Linux Shell code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write HTML Code": {
            "Prefix":   r"Please write HTML code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write CSS Code": {
            "Prefix":   r"Please write CSS code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Write C++ Code": {
            "Prefix":   r"Please write C++ code based on the following description: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Explain Code": {
            "Prefix":   r"Please explain the following code: " + "\n```\n",
            "Suffix":   "\n```\n",
        },
        "Literature to Bib": {
            "Prefix":   r"Here are some bibliography items, please transform them into bibtex style." +
                        r"Note that, reference styles maybe more than one kind, you should transform each item correctly." +
                        r"Items need to be transformed:",
            "Suffix":   r"",
            "Visible": True,
        },
    }
