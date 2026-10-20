pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import ".." as Design

/** 输出契约面板：只读等宽文本。文案由应用固定生成，界面无编辑入口。
 *
 * 正文经 `panelText` 传入：父级只在抽屉展开且停在契约页时填充，避免无谓取值。
 */
ScrollView {
    id: root

    /** 契约全文；空串即未展开。 */
    property string panelText: ""

    anchors.margins: 1
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    TextArea {
        leftPadding: Design.Theme.space3
        rightPadding: Design.Theme.space3
        topPadding: Design.Theme.space3
        bottomPadding: Design.Theme.space3
        verticalAlignment: TextEdit.AlignTop
        background: null
        readOnly: true
        selectByMouse: true
        text: root.panelText
        wrapMode: TextArea.Wrap
        color: Design.Theme.textSecondary
        selectionColor: Design.Theme.accent
        selectedTextColor: Design.Theme.textOnAccent
        font.family: "Consolas"
        font.pixelSize: Design.Theme.captionFontSize
    }
}
