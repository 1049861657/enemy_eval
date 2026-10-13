pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    required property var controller

    readonly property bool busy: root.controller.aiBusy
    readonly property bool configured: root.controller.aiConfigured
    readonly property var cardData: JSON.parse(root.controller.enemyDataJson)
    readonly property string defaultPrompt: root.controller.aiDefaultPrompt()
    readonly property bool promptCustom: promptArea.text.trim().length > 0
                                         && promptArea.text !== root.defaultPrompt
    readonly property bool promptDirty: promptArea.text !== root.savedPrompt
    readonly property bool hasResult: root.suggestion.length > 0
    readonly property bool generating: root.busy && !root.hasResult
    readonly property bool edited: root.hasResult && suggestionArea.text !== root.suggestion
    readonly property bool canAdopt: root.hasResult && !root.busy
                                     && suggestionArea.text.trim().length > 0

    /** 最近一次成功结果的副本；编辑框可改，「还原」回到此值。 */
    property string suggestion: ""
    property bool promptExpanded: false
    /** 抽屉页：0 = 提示词，1 = 实际请求。 */
    property int drawerTab: 0
    /** 本次请求已等待的秒数。 */
    property int elapsed: 0
    /** 偏好里已落盘的提示词文本；编辑框与之不同即有未保存改动。未保存的改动仍用于本次生成。 */
    property string savedPrompt: ""

    function savePrompt() {
        if (!root.controller.saveAiPrompt(promptArea.text))
            return
        root.savedPrompt = promptArea.text
        savedHint.opacity = 1
        savedHintTimer.restart()
    }

    function generate() {
        if (!root.configured) {
            root.controller.requestAiSettings()
            return
        }
        root.controller.requestAiReview(promptArea.text)
    }

    function adopt() {
        if (root.controller.applyAiComment(suggestionArea.text))
            root.close()
    }

    function stateText() {
        if (root.busy)
            return "生成中 · " + root.elapsed + "s"
        if (root.edited)
            return "已改动"
        if (root.hasResult)
            return suggestionArea.text.length + " 字"
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
        root.savedPrompt = root.controller.aiPromptText()
        promptArea.text = root.savedPrompt
        root.suggestion = root.controller.aiComment
        suggestionArea.text = root.suggestion
        root.promptExpanded = false
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
            suggestionArea.text = root.suggestion
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
                icon.source: "icons/close.svg"
                icon.width: 20
                icon.height: 20
                display: AbstractButton.IconOnly
                toolTipText: "关闭 (Esc)"
                onClicked: root.close()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 150
            Layout.preferredHeight: 220
            radius: Design.Theme.radiusMedium
            color: Design.Theme.surface
            border.width: 1
            border.color: suggestionArea.activeFocus ? Design.Theme.borderStrong
                          : root.hasResult ? Design.Theme.accent
                          : Design.Theme.border
            clip: true

            Behavior on border.color {
                ColorAnimation {
                    duration: 160
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    Layout.leftMargin: Design.Theme.space4
                    Layout.rightMargin: Design.Theme.space4
                    spacing: Design.Theme.space2

                    Label {
                        Layout.alignment: Qt.AlignVCenter
                        text: "建议"
                        color: root.hasResult ? Design.Theme.accentHover : Design.Theme.textSecondary
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                        font.weight: Font.DemiBold
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Label {
                        Layout.alignment: Qt.AlignVCenter
                        text: root.stateText()
                        color: root.busy ? Design.Theme.accentHover : Design.Theme.textPlaceholder
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                    }

                    Label {
                        Layout.alignment: Qt.AlignVCenter
                        visible: root.edited && !root.busy
                        text: "还原"
                        color: restoreArea.containsMouse ? Design.Theme.accentPressed
                                                         : Design.Theme.accent
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                        font.underline: restoreArea.containsMouse

                        MouseArea {
                            id: restoreArea

                            anchors.fill: parent
                            anchors.margins: -4
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: suggestionArea.text = root.suggestion
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.hasResult
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    TextArea {
                        id: suggestionArea

                        readOnly: root.busy
                        leftPadding: Design.Theme.space4
                        rightPadding: Design.Theme.space4
                        topPadding: 0
                        bottomPadding: Design.Theme.space4
                        verticalAlignment: TextEdit.AlignTop
                        background: null
                        wrapMode: TextArea.Wrap
                        selectByMouse: true
                        opacity: root.busy ? 0.4 : 1
                        color: Design.Theme.textPrimary
                        selectionColor: Design.Theme.accent
                        selectedTextColor: Design.Theme.textOnAccent
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.bodyFontSize + 1

                        Behavior on opacity {
                            NumberAnimation {
                                duration: 140
                                easing.type: Easing.OutCubic
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: !root.hasResult

                    Label {
                        anchors.centerIn: parent
                        visible: !root.generating
                        text: root.configured ? "生成后可直接修改，再采纳" : "未配置 AI 服务"
                        color: root.configured ? Design.Theme.textPlaceholder : Design.Theme.warning
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.bodyFontSize
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Design.Theme.space4
                        anchors.rightMargin: Design.Theme.space4
                        anchors.topMargin: Design.Theme.space1
                        visible: root.generating
                        spacing: Design.Theme.space3

                        Repeater {
                            model: [1, 0.92, 0.55]

                            Rectangle {
                                id: skeletonBar

                                required property int index
                                required property real modelData

                                Layout.preferredWidth: parent.width * skeletonBar.modelData
                                Layout.preferredHeight: 12
                                radius: 6
                                color: Design.Theme.disabledSurface

                                SequentialAnimation on opacity {
                                    running: root.generating && root.visible
                                    loops: Animation.Infinite
                                    PauseAnimation {
                                        duration: skeletonBar.index * 160
                                    }
                                    NumberAnimation {
                                        to: 0.35
                                        duration: 620
                                        easing.type: Easing.InOutSine
                                    }
                                    NumberAnimation {
                                        to: 1
                                        duration: 620
                                        easing.type: Easing.InOutSine
                                    }
                                }
                            }
                        }

                        Item {
                            Layout.fillHeight: true
                        }
                    }
                }
            }

            Item {
                id: progressTrack

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 1
                height: 2
                visible: root.busy
                clip: true

                Rectangle {
                    width: progressTrack.width * 0.3
                    height: parent.height
                    radius: 1
                    color: Design.Theme.accent

                    NumberAnimation on x {
                        running: root.busy && root.visible
                        loops: Animation.Infinite
                        from: -progressTrack.width * 0.3
                        to: progressTrack.width
                        duration: 1100
                        easing.type: Easing.InOutCubic
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 214
            visible: root.promptExpanded
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
                        text: "提示词"
                    }

                    DrawerTab {
                        tabIndex: 1
                        text: "实际请求"
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Label {
                        id: savedHint

                        Layout.alignment: Qt.AlignVCenter
                        Layout.rightMargin: Design.Theme.space1
                        visible: root.drawerTab === 0 && !root.promptDirty
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
                        visible: root.drawerTab === 0 && promptArea.text !== root.defaultPrompt
                        text: "恢复默认"
                        appearance: "subtle"
                        font.pixelSize: Design.Theme.captionFontSize
                        enabled: !root.busy
                        onClicked: promptArea.text = root.defaultPrompt
                    }

                    AppButton {
                        Layout.preferredHeight: 26
                        visible: root.drawerTab === 0 && root.promptDirty
                        text: "撤销修改"
                        appearance: "subtle"
                        font.pixelSize: Design.Theme.captionFontSize
                        onClicked: promptArea.text = root.savedPrompt
                    }

                    AppButton {
                        Layout.preferredHeight: 26
                        visible: root.drawerTab === 0 && root.promptDirty
                        text: "保存"
                        font.pixelSize: Design.Theme.captionFontSize
                        onClicked: root.savePrompt()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Design.Theme.radiusSmall
                    color: Design.Theme.surface
                    border.width: 1
                    border.color: promptArea.activeFocus ? Design.Theme.borderStrong : Design.Theme.border

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 1
                        visible: root.drawerTab === 0
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        TextArea {
                            id: promptArea

                            leftPadding: Design.Theme.space3
                            rightPadding: Design.Theme.space3
                            topPadding: Design.Theme.space3
                            bottomPadding: Design.Theme.space3
                            verticalAlignment: TextEdit.AlignTop
                            background: null
                            placeholderText: "留空使用默认"
                            placeholderTextColor: Design.Theme.textPlaceholder
                            wrapMode: TextArea.Wrap
                            selectByMouse: true
                            readOnly: root.busy
                            color: Design.Theme.textPrimary
                            selectionColor: Design.Theme.accent
                            selectedTextColor: Design.Theme.textOnAccent
                            font.family: Design.Theme.fontFamily
                            font.pixelSize: Design.Theme.captionFontSize + 1
                        }
                    }

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 1
                        visible: root.drawerTab === 1
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
                            text: root.promptExpanded && root.drawerTab === 1
                                  ? root.controller.aiRequestPreview(promptArea.text)
                                  : ""
                            wrapMode: TextArea.Wrap
                            color: Design.Theme.textSecondary
                            selectionColor: Design.Theme.accent
                            selectedTextColor: Design.Theme.textOnAccent
                            font.family: "Consolas"
                            font.pixelSize: Design.Theme.captionFontSize
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            AppButton {
                Layout.alignment: Qt.AlignVCenter
                text: root.promptDirty ? "提示词 · 未保存"
                      : root.promptCustom ? "提示词 · 自定义" : "提示词"
                appearance: "command"
                active: root.promptExpanded
                menu: true
                onClicked: root.promptExpanded = !root.promptExpanded
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
                iconSource: root.configured && !root.hasResult && !root.busy ? "icons/radar.svg" : ""
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
