from kag.common.utils import extract_tag_content


def run_extra_tag():
    test_cases = [
        {
            "input": "<tag1>abced</tag1>some word<tag2>other tags</tag2>",
            "expected": [("tag1", "abced"), ("", "some word"), ("tag2", "other tags")],
            "description": "基本闭合标签与无标签文本混合",
        },
        {
            "input": "<p>Hello <b>world</b> this is <i>test</i>",
            "expected": [
                ("p", "Hello "),
                ("b", "world"),
                ("", " this is "),
                ("i", "test"),
            ],
            "description": "混合闭合与未闭合标签",
        },
        {
            "input": "plain text without any tags",
            "expected": [("", "plain text without any tags")],
            "description": "纯文本无标签",
        },
        {
            "input": "<div>\n    Line 1\n    <span>Line 2</span>\n    Line 3\n</div>",
            "expected": [
                ("div", "\n    Line 1\n    <span>Line 2</span>\n    Line 3\n")
            ],
            "description": "多行内容和空白处理",
        },
        {
            "input": "<a>A</a><b>B</b><c>C</c>",
            "expected": [("a", "A"), ("b", "B"), ("c", "C")],
            "description": "连续多个闭合标签",
        },
        {
            "input": "<title>My Document</title><content>This is the content",
            "expected": [("title", "My Document"), ("content", "This is the content")],
            "description": "未闭合标签（EOF结尾）",
        },
        {
            "input": "<log>Error: &*^%$#@!;</log><note>End of log</note>",
            "expected": [("log", "Error: &*^%$#@!;"), ("note", "End of log")],
            "description": "含特殊字符的内容",
        },
        {
            "input": "",
            "expected": [],
            "description": "空字符串输入",
        },
    ]

    for i, test in enumerate(test_cases):
        result = extract_tag_content(test["input"])
        assert (
            result == test["expected"]
        ), f"Test {i+1} failed: {test['description']}\nGot: {result}\nExpected: {test['expected']}"
        print(f"Test {i+1} passed: {test['description']}")


if __name__ == "__main__":
    run_extra_tag()
