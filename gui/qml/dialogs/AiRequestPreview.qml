pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import ".." as Design

/** 实际请求预览面板：只读等宽文本，内容为组装后真正会发出的两条 message。
 *
 * 正文经 `panelText` 传入：父级只在抽屉展开且停在预览页时按当前人设取值，与发请求同源。
 */
ScrollView {
    id: root

    /** 预览正文；空串即未展开。 */
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
