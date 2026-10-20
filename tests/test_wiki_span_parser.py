"""core.render.text.wikitext_spans：wikitext → 绘制用片段解析与换行的单元测试。"""

from __future__ import annotations

from core.render.text.wikitext_spans import (
    TextSpan,
    WikiStyle,
    parse_wikitext_to_spans,
    wrap_spans_to_lines,
)


class TestParseWikitextToSpans:
    def test_plain_text_becomes_single_span(self):
        spans = parse_wikitext_to_spans("普通文本")
        assert len(spans) == 1
        assert spans[0].text == "普通文本"
        assert spans[0].style == WikiStyle()

    def test_bold_markup_produces_bold_span(self):
        spans = parse_wikitext_to_spans("前文'''加粗文字'''后文")
        assert [s.text for s in spans] == ["前文", "加粗文字", "后文"]
        assert spans[1].style.bold is True
        assert spans[0].style.bold is False

    def test_unclosed_bold_markup_is_treated_as_literal_text(self):
        # 找不到配对的 ''' 时不应抛异常或丢字符，整体退化为纯文本处理
        spans = parse_wikitext_to_spans("前文'''未闭合")
        joined = "".join(s.text for s in spans)
        assert "未闭合" in joined

    def test_color_template_applies_custom_color(self):
        spans = parse_wikitext_to_spans("{{color|#ff0000|红色文字}}")
        assert len(spans) == 1
        assert spans[0].text == "红色文字"
        assert spans[0].style.color == (1.0, 0.0, 0.0, 1.0)

    def test_link_template_shows_display_text_only(self):
        spans = parse_wikitext_to_spans("[[某某条目|显示名]]")
        assert len(spans) == 1
        assert spans[0].text == "显示名"

    def test_link_without_display_text_shows_target(self):
        spans = parse_wikitext_to_spans("[[某某条目]]")
        assert spans[0].text == "某某条目"

    def test_shu_yu_template_underlines_display_text(self):
        spans = parse_wikitext_to_spans("{{术语|概述|杂兵}}")
        assert spans[0].text == "杂兵"
        assert spans[0].style.underline is True

    def test_yichang_xiaoguo_template_concatenates_effect_and_value(self):
        # PRTS 模板:异常效果 别名 眩晕→晕眩，第二无名参数拼到显示名后
        spans = parse_wikitext_to_spans("{{异常效果|眩晕|100%}}")
        assert spans[0].text == "晕眩100%"
        assert spans[0].style.bold is True
        assert spans[0].style.color is not None

    def test_yichang_xiaoguo_single_name_shows_as_link_term(self):
        spans = parse_wikitext_to_spans("{{异常效果|孤立}}")
        assert spans[0].text == "孤立"
        assert spans[0].style.bold is True
        assert spans[0].style.color is not None

    def test_teshu_jizhi_shows_mechanism_name_as_link_term(self):
        spans = parse_wikitext_to_spans("{{特殊机制|非首要目标}}")
        assert spans[0].text == "非首要目标"
        assert spans[0].style.bold is True
        assert spans[0].style.color is not None

    def test_unknown_named_params_are_not_dumped_into_body(self):
        spans = parse_wikitext_to_spans("前{{未知模板|内容=不该出现}}后")
        joined = "".join(s.text for s in spans)
        assert joined == "前后"
        assert "内容=" not in joined

    def test_popup_template_renders_as_hint_mark_without_tooltip_body(self):
        # 内容里的 <br> 不得先于模板闭合被拆行，否则注释后半段会漏到正文
        spans = parse_wikitext_to_spans(
            "会打断当前动画能力{{popup|内容=能力【披萨轰炸】本身也是动画能力。"
            "<br>又因为前摇结束离被打断很近（受{{术语|ba.slowdown|迟钝}}影响）。}}"
            "）<br>※能力说明"
        )
        joined = "".join(s.text for s in spans)
        assert joined == "会打断当前动画能力?）\n※能力说明"
        assert "又因为前摇" not in joined
        assert "内容=" not in joined
        assert "}}" not in joined
        assert spans[1].style.hint is True

    def test_multiline_text_parsed_line_by_line_and_flattened(self):
        spans = parse_wikitext_to_spans("第一行\n第二行")
        joined = "".join(s.text for s in spans)
        assert "第一行" in joined and "第二行" in joined

    def test_empty_string_yields_no_spans(self):
        assert parse_wikitext_to_spans("") == []

    def test_adjacent_spans_with_same_style_are_merged(self):
        # 加粗结束后紧跟同样式的空模板/边界，合并逻辑不应产生冗余的相邻同样式片段
        spans = parse_wikitext_to_spans("普通A普通B")
        assert len(spans) == 1
        assert spans[0].text == "普通A普通B"


class TestWrapSpansToLines:
    @staticmethod
    def _fixed_width_measure(ch: str, style: WikiStyle) -> float:
        # 每个字符固定宽度，便于精确断言换行位置，不依赖真实字体测量
        return 10.0

    def test_wraps_long_text_into_multiple_lines_by_width(self):
        spans = [TextSpan("一二三四五六", WikiStyle())]
        lines = wrap_spans_to_lines(spans, max_width=30, measure=self._fixed_width_measure)
        # 每行最多 3 个字符（30 / 10），6 个字符应拆成至少 2 行
        assert len(lines) >= 2
        total_chars = sum(len(span.text) for line in lines for span in line)
        assert total_chars == 6

    def test_empty_spans_yields_one_empty_line(self):
        # 换行算法保证至少一行（即使没有内容），不会返回完全空的行列表
        assert wrap_spans_to_lines([], max_width=100, measure=self._fixed_width_measure) == [[]]

    def test_preserves_span_style_across_wrapped_lines(self):
        bold_style = WikiStyle(bold=True)
        spans = [TextSpan("加粗内容文字", bold_style)]
        lines = wrap_spans_to_lines(spans, max_width=20, measure=self._fixed_width_measure)
        for line in lines:
            for span in line:
                assert span.style.bold is True
