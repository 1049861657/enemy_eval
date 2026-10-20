pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import ".." as Design

/** 人设编辑面板：多行文本 + 只读态。
 *
 * 正文用 `text` 别名交给父级（父级据此判定是否已改、是否与默认相同，并持有落盘副本）。
 */
ScrollView {
    id: root

    /** 人设正文；父级经别名读写。 */
    property alias text: personaArea.text
    /** 编辑框当前持有焦点（父级据此调描边）；`activeFocus` 是 Item 的 FINAL 属性，不能别名覆盖。 */
    readonly property bool editing: personaArea.activeFocus
    /** 生成中：只读，避免与在飞请求的人设漂移。 */
    property alias readOnly: personaArea.readOnly

    anchors.margins: 1
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    TextArea {
        id: personaArea

        leftPadding: Design.Theme.space3
        rightPadding: Design.Theme.space3
        topPadding: Design.Theme.space3
        bottomPadding: Design.Theme.space3
        verticalAlignment: TextEdit.AlignTop
        background: null
        placeholderText: "留空使用默认人设"
        placeholderTextColor: Design.Theme.textPlaceholder
        wrapMode: TextArea.Wrap
        selectByMouse: true
        color: Design.Theme.textPrimary
        selectionColor: Design.Theme.accent
        selectedTextColor: Design.Theme.textOnAccent
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.captionFontSize + 1
    }
}
