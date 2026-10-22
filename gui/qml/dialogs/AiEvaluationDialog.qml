pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import ".." as Design

/** AI 简评弹窗：只做状态与信号编排；视图拆在 AiResultPanel / AiPersonaPanel /
 *  AiContractPanel / AiRequestPreview。
 *
 * 状态归属：人设正文在 `AiPersonaPanel.text`、建议正文在 `AiResultPanel.text`（都是别名），
 * 判定（`personaCustom` / `personaDirty` / `hasResult` / `edited` / `canAdopt`）与文案
 * （`stateText()`）都在本文件；子组件不读 controller，只收属性。
 */
Dialog {
    id: root

    required property var controller

    readonly property bool busy: root.controller.aiBusy
    readonly property bool configured: root.controller.aiConfigured
    readonly property var cardData: JSON.parse(root.controller.enemyDataJson)
    readonly property string defaultPersona: root.controller.aiDefaultPersona()
    readonly property string contractText: root.controller.aiContractText()
    readonly property bool personaCustom: personaPanel.text.trim().length > 0
                                          && personaPanel.text !== root.defaultPersona
    readonly property bool personaDirty: personaPanel.text !== root.savedPersona
    readonly property bool hasResult: root.suggestion.length > 0
    readonly property bool generating: root.busy && !root.hasResult
    readonly property bool edited: root.hasResult && resultPanel.text !== root.suggestion
    readonly property bool canAdopt: root.hasResult && !root.busy
                                     && resultPanel.text.trim().length > 0

    /** 最近一次成功结果的副本；编辑框可改，「还原」回到此值。 */
    property string suggestion: ""
    property bool drawerExpanded: false
    /** 抽屉页：0 = 人设，1 = 输出契约，2 = 实际请求。 */
    property int drawerTab: 0
    /** 本次请求已等待的秒数。 */
    property int elapsed: 0
    /** 偏好里已落盘的人设文本；编辑框与之不同即有未保存改动。未保存的改动仍用于本次生成。 */
    property string savedPersona: ""

    function savePersona() {
        if (!root.controller.saveAiPersona(personaPanel.text))
            return
        root.savedPersona = personaPanel.text
        savedHint.opacity = 1
        savedHintTimer.restart()
    }

    function generate() {
        if (!root.configured) {
            root.controller.requestSettings("ai")
            return
        }
        root.controller.requestAiReview(personaPanel.text)
    }

    function adopt() {
        if (root.controller.applyAiComment(resultPanel.text))
            root.close()
    }

    function stateText() {
        if (root.busy)
            return "生成中 · " + root.elapsed + "s"
        if (root.edited)
            return "已改动"
        if (root.hasResult)
            return resultPanel.text.length + " 字"
        return ""
    }

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 48 : 680, 680)
    height: Math.min(parent ? parent.height - 72 : implicitHeight, implicitHeight)
    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5

    onBusyChanged: {
        if (root.busy)
            root.elapsed = 0
    }

    onOpened: {
        root.savedPersona = root.controller.aiPersonaText()
        personaPanel.text = root.savedPersona
        root.suggestion = root.controller.aiComment
        resultPanel.text = root.suggestion
        root.drawerExpanded = false
        root.drawerTab = 0
        savedHint.opacity = 0
    }

    onClosed: {
        if (root.busy)
            root.controller.abandonAiReview()
    }

    Connections {
        target: root.controller

        function onAiCommentReady() {
            root.suggestion = root.controller.aiComment
            resultPanel.text = root.suggestion
        }
    }

    Timer {
        interval: 1000
        repeat: true
        running: root.busy && root.visible
        onTriggered: root.elapsed += 1
    }

    Timer {
        id: savedHintTimer

        interval: 1600
        onTriggered: savedHint.opacity = 0
    }

    Overlay.modal: Rectangle {
        color: Design.Theme.overlay
    }

    background: Rectangle {
        color: Design.Theme.surface
        radius: Design.Theme.radiusLarge
        border.width: 1
        border.color: Design.Theme.border
    }

    enter: Transition {
        NumberAnimation {
            property: "opacity"
            from: 0
            to: 1
            duration: 150
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            property: "scale"
            from: 0.975
            to: 1
            duration: 170
            easing.type: Easing.OutCubic
        }
    }

    exit: Transition {
        NumberAnimation {
            property: "opacity"
            from: 1
            to: 0
            duration: 90
            easing.type: Easing.InCubic
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 170
            easing.type: Easing.OutCubic
        }
    }

    component DrawerTab: ToolButton {
        id: tab

        required property int tabIndex
        readonly property bool selected: root.drawerTab === tab.tabIndex

        hoverEnabled: true
        implicitHeight: 26
        leftPadding: Design.Theme.space3
        rightPadding: Design.Theme.space3
        topPadding: 0
        bottomPadding: 0
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.captionFontSize
        font.weight: Font.Medium
        onClicked: root.drawerTab = tab.tabIndex

        contentItem: Label {
            text: tab.text
            color: tab.selected ? Design.Theme.textPrimary : Design.Theme.textSecondary
            font: tab.font
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: 4
            color: tab.selected ? Design.Theme.tabSelected
                   : tab.down ? Design.Theme.tabPressed
                   : tab.hovered ? Design.Theme.tabHover
                   : "transparent"
            border.width: tab.selected ? 1 : 0
            border.color: Design.Theme.border

            Design.AppFocusFrame {
                active: tab.visualFocus
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space4

        Shortcut {
            enabled: root.visible && !root.busy
            sequences: ["Ctrl+Return", "Ctrl+Enter"]
            onActivated: root.generate()
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space3

            Label {
                Layout.alignment: Qt.AlignVCenter
                text: "AI 简评"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize + 3
                font.weight: Font.DemiBold
            }

            Label {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                text: [String(root.cardData.name || ""), root.controller.aiModel]
                      .filter(part => part.length > 0).join(" · ")
                color: Design.Theme.textPlaceholder
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
                elide: Text.ElideRight
            }

            AppIconButton {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 32
                implicitHeight: 32
                leftPadding: 0
                rightPadding: 0
                topPadding: 0
                bottomPadding: 0
                icon.source: "../icons/close.svg"
                icon.width: 20
                icon.height: 20
                display: AbstractButton.IconOnly
                toolTipText: "关闭 (Esc)"
                onClicked: root.close()
            }
        }

        AiResultPanel {
            id: resultPanel

            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 150
            Layout.preferredHeight: 220
            suggestionText: root.suggestion
            stateText: root.stateText()
            busy: root.busy
            hasResult: root.hasResult
            generating: root.generating
            configured: root.configured
            edited: root.edited
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 214
            visible: root.drawerExpanded
            radius: Design.Theme.radiusMedium
            color: Design.Theme.surfaceSubtle

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Design.Theme.space2
                spacing: Design.Theme.space2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Design.Theme.space1

                    DrawerTab {
                        tabIndex: 0
                        text: "人设"
                    }

                    DrawerTab {
                        tabIndex: 1
                        text: "输出契约"
                    }

                    DrawerTab {
                        tabIndex: 2
                        text: "实际请求"
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Label {
                        id: savedHint

                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: Design.Theme.space1
                        visible: root.drawerTab === 0 && !root.personaDirty
                        opacity: 0
                        text: "✓ 已保存"
                        color: Design.Theme.success
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize

                        Behavior on opacity {
                            NumberAnimation {
                                duration: 200
                                easing.type: Easing.OutCubic
                            }
                        }
                    }

                    AppButton {
                        Layout.preferredHeight: 26
                        visible: root.drawerTab === 0 && personaPanel.text !== root.defaultPersona
                        text: "恢复默认"
                        appearance: "subtle"
                        font.pixelSize: Design.Theme.captionFontSize
                        enabled: !root.busy
                        onClicked: personaPanel.text = root.defaultPersona
                    }

                    AppButton {
                        Layout.preferredHeight: 26
                        visible: root.drawerTab === 0 && root.personaDirty
                        text: "撤销修改"
                        appearance: "subtle"
                        font.pixelSize: Design.Theme.captionFontSize
                        onClicked: personaPanel.text = root.savedPersona
                    }

                    AppButton {
                        Layout.preferredHeight: 26
                        visible: root.drawerTab === 0 && root.personaDirty
                        text: "保存"
                        font.pixelSize: Design.Theme.captionFontSize
                        onClicked: root.savePersona()
                    }
                }

                Label {
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? implicitHeight : 0
                    visible: root.drawerTab !== 2
                    text: root.drawerTab === 0
                          ? "只影响语气与措辞；输出格式与评价口径固定，不可修改。"
                          : "由应用固定生成，随版本升级更新；此处只读。"
                    color: Design.Theme.textPlaceholder
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.captionFontSize
                    elide: Text.ElideRight
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Design.Theme.radiusSmall
                    color: Design.Theme.surface
                    border.width: 1
                    border.color: personaPanel.editing ? Design.Theme.borderStrong : Design.Theme.border

                    AiPersonaPanel {
                        id: personaPanel

                        anchors.fill: parent
                        visible: root.drawerTab === 0
                        readOnly: root.busy
                    }

                    AiContractPanel {
                        anchors.fill: parent
                        visible: root.drawerTab === 1
                        panelText: root.drawerExpanded && root.drawerTab === 1 ? root.contractText : ""
                    }

                    AiRequestPreview {
                        anchors.fill: parent
                        visible: root.drawerTab === 2
                        panelText: root.drawerExpanded && root.drawerTab === 2
                                   ? root.controller.aiRequestPreview(personaPanel.text) : ""
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            AppButton {
                Layout.alignment: Qt.AlignVCenter
                text: root.personaDirty ? "人设 · 未保存"
                      : root.personaCustom ? "人设 · 自定义" : "人设"
                appearance: "command"
                active: root.drawerExpanded
                menu: true
                onClicked: root.drawerExpanded = !root.drawerExpanded
            }

            Item {
                Layout.fillWidth: true
            }

            AppButton {
                Layout.alignment: Qt.AlignVCenter
                text: !root.configured ? "去设置"
                      : root.busy ? "生成中…"
                      : root.hasResult ? "重新生成" : "生成"
                appearance: root.hasResult ? "secondary" : "primary"
                iconSource: root.configured && !root.hasResult && !root.busy ? "../icons/radar.svg" : ""
                enabled: !root.busy
                ToolTip.visible: hovered && root.configured
                ToolTip.text: "Ctrl+Enter"
                onClicked: root.generate()
            }

            AppButton {
                Layout.alignment: Qt.AlignVCenter
                visible: root.hasResult
                text: "采纳"
                enabled: root.canAdopt
                onClicked: root.adopt()
            }
        }
    }
}
