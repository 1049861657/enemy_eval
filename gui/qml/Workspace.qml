pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Item {
    id: root

    required property var controller

    property var enemyData: ({})
    property var recentFiles: []
    property bool schemaEditMode: false
    property bool schemaSaveAsTemplate: false
    property var schemaDraft: []
    property int schemaNewSerial: 0
    property var fieldErrors: ({})
    property string toastText: ""
    property string toastTone: "info"
    property var toastStyle: root.toastStyleFor(root.toastTone)
    property string detailedTarget: ""
    property int detailedSkillIndex: -1
    property string recentPendingRemoval: ""

    function refreshData(serialized, clearErrors) {
        enemyData = JSON.parse(serialized)
        if (clearErrors !== false)
            fieldErrors = ({})
    }

    function beginSchemaEdit() {
        var ratings = root.enemyData.ratings || []
        var draft = []
        for (var i = 0; i < ratings.length; ++i)
            draft.push({ id: String(i), name: ratings[i].name })
        schemaNewSerial = 0
        schemaSaveAsTemplate = false
        schemaDraft = draft
        schemaEditMode = true
    }

    function refreshRecentFiles(serialized) {
        recentFiles = JSON.parse(serialized)
    }

    function clearFieldError(field) {
        if (root.fieldErrors[field] === undefined)
            return
        var errors = Object.assign({}, root.fieldErrors)
        delete errors[field]
        root.fieldErrors = errors
    }

    function commit(field, value) {
        root.controller.updateProperty(field, JSON.stringify(value))
    }

    function commitAttackType(value) {
        if (value === "近战" || value === "不攻击")
            root.controller.updateProperties(JSON.stringify({
                attack_type: value,
                attack_range_radius: 0
            }))
        else
            commit("attack_type", value)
    }

    function openPrtsDialog() {
        prtsDialog.open()
    }

    function toastStyleFor(tone) {
        switch (tone) {
        case "success":
            return { color: Design.Theme.success, subtle: Design.Theme.successSubtle, glyph: "✓" }
        case "warning":
            return { color: Design.Theme.warning, subtle: Design.Theme.warningSubtle, glyph: "!" }
        case "error":
            return { color: Design.Theme.danger, subtle: Design.Theme.dangerSubtle, glyph: "!" }
        default:
            return { color: Design.Theme.accent, subtle: Design.Theme.accentSubtle, glyph: "i" }
        }
    }

    function showToast(message, tone) {
        toastText = message
        toastTone = tone
        var overlay = Overlay.overlay
        if (overlay && toast.parent !== overlay) {
            toast.parent = overlay
            toast.z = 1
        }
        toastTimer.restart()
    }

    function confirmNewCard(isReset) {
        newCardDialog.dialogTitle = isReset
                ? "恢复默认数据？"
                : "丢弃当前内容并新建？"
        newCardDialog.message = isReset
                ? "当前编辑内容将被默认数据替换。"
                : "所有未保存的修改都将丢失。"
        newCardDialog.confirmText = isReset ? "恢复默认" : "丢弃并新建"
        newCardDialog.open()
    }

    function confirmRemoveRecent(path, name) {
        recentPendingRemoval = path
        removeRecentDialog.dialogTitle = name
        removeRecentDialog.message = "文件已不存在，是否从最近打开中移除该记录？"
        removeRecentDialog.open()
    }

    function openDetailed(target, title, value, skillIndex) {
        detailedTarget = target
        detailedSkillIndex = skillIndex === undefined ? -1 : skillIndex
        detailedDialog.openFor(title, value)
    }

    function updateBannerText(tag) {
        if (!tag)
            return ""
        var head = tag.charAt(0)
        if (head === "v" || head === "V")
            return "发现新版本 " + tag
        return "发现新版本 v" + tag
    }

    function saveDetailed(value) {
        if (detailedTarget === "skillEffect")
            root.controller.skills.updateField(detailedSkillIndex, "效果", value)
        else
            commit(detailedTarget, value)
    }

    Component.onCompleted: {
        refreshData(root.controller.enemyDataJson, true)
        refreshRecentFiles(root.controller.recentFilesJson)
    }

    Connections {
        target: root.controller
        function onEnemyDataChanged(serialized) { root.refreshData(serialized, true) }
        function onRecentFilesChanged(serialized) { root.refreshRecentFiles(serialized) }
        function onRemoveRecentConfirmRequested(path, name) { root.confirmRemoveRecent(path, name) }
        function onMessageChanged(message, tone) { root.showToast(message, tone) }
        function onFieldError(field, message) {
            var errors = Object.assign({}, root.fieldErrors)
            errors[field] = message
            root.fieldErrors = errors
            root.showToast(message, "error")
            root.refreshData(root.controller.enemyDataJson, false)
        }
        function onDialogRequested(title, message, tone) {
            messageDialog.show(title, message, tone)
        }
        function onAboutRequested() {
            aboutDialog.open()
        }
        function onAiSettingsRequested() {
            aiSettingsDialog.open()
        }
        function onLightDismissRequested() {
            commandBar.closeMenus()
            Design.Theme.lightDismiss()
        }
    }

    readonly property bool historyKeysEnabled: {
        var focused = root.Window.activeFocusItem
        return !(focused instanceof TextInput || focused instanceof TextEdit)
    }

    Shortcut { sequence: "Ctrl+Z"; enabled: root.historyKeysEnabled; onActivated: root.controller.requestUndo() }
    Shortcut { sequence: "Ctrl+Shift+Z"; enabled: root.historyKeysEnabled; onActivated: root.controller.requestRedo() }
    Shortcut { sequence: "Ctrl+Y"; enabled: root.historyKeysEnabled; onActivated: root.controller.requestRedo() }
    Shortcut { sequence: "Ctrl+N"; onActivated: root.confirmNewCard(false) }
    Shortcut { sequence: "Ctrl+O"; onActivated: root.controller.requestOpen() }
    Shortcut { sequence: "Ctrl+S"; onActivated: root.controller.requestSave() }
    Shortcut { sequence: "Ctrl+E"; onActivated: root.controller.requestExport() }
    Shortcut { sequence: "F5"; onActivated: root.controller.requestRefresh() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.controller.requestQuit() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CommandBar {
            id: commandBar
            Layout.fillWidth: true
            workspace: root
        }

        Rectangle {
            id: updateBanner
            Layout.fillWidth: true
            visible: root.controller.updateBannerTag !== ""
            implicitHeight: bannerRow.implicitHeight + Design.Theme.space3 * 2
            color: Design.Theme.accentSubtle

            RowLayout {
                id: bannerRow
                anchors.fill: parent
                anchors.leftMargin: Design.Theme.space4
                anchors.rightMargin: Design.Theme.space4
                spacing: Design.Theme.space3

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: root.updateBannerText(root.controller.updateBannerTag)
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize
                    color: Design.Theme.textPrimary
                }

                AppButton {
                    text: "查看"
                    appearance: "secondary"
                    enabled: root.controller.updateBannerUrl !== ""
                    onClicked: Qt.openUrlExternally(root.controller.updateBannerUrl)
                }

                AppButton {
                    text: "忽略此版本"
                    appearance: "subtle"
                    onClicked: root.controller.dismissUpdate(root.controller.updateBannerTag)
                }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Pane {
                SplitView.preferredWidth: Math.min(520, root.width * 0.38)
                SplitView.minimumWidth: 360
                padding: Design.Theme.space3

                background: Rectangle { color: Design.Theme.surfaceSubtle }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Design.Theme.space3

                    TabBar {
                        id: editorTabs
                        objectName: "editorTabs"
                        Layout.fillWidth: true
                        currentIndex: 0
                        implicitHeight: 48
                        padding: Design.Theme.space1
                        spacing: Design.Theme.space1

                        background: Rectangle {
                            radius: Design.Theme.radiusMedium
                            color: Design.Theme.tabTrack
                            border.width: 1
                            border.color: Design.Theme.border
                        }

                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "基础"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "战斗"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "抗性"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "技能"
                        }
                        AppTabButton {
                            width: (editorTabs.availableWidth - editorTabs.spacing * 4) / 5
                            text: "评价"
                        }
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: editorTabs.currentIndex

                        EditorBasicsPage { workspace: root }
                        EditorCombatPage { workspace: root }
                        EditorResistPage { workspace: root }
                        EditorSkillsPage { workspace: root }
                        EditorRatingPage { workspace: root }
                    }
                }
            }

            Pane {
                SplitView.fillWidth: true
                padding: Design.Theme.space4
                background: Rectangle { color: Design.Theme.surfaceCanvas }

                PreviewViewport {
                    anchors.fill: parent
                    source: "image://enemy-card/current?revision="
                            + root.controller.previewRevision
                    busy: root.controller.busy
                    prtsLevelsJson: root.controller.prtsLevelsJson
                    prtsLevelIndex: root.controller.prtsLevelIndex
                    onPrtsLevelChangeRequested: (levelIndex) => root.controller.requestPrtsLevelChange(levelIndex)
                    onExportRequested: root.controller.requestExport()
                }
            }
        }
    }

    Rectangle {
        id: toast
        z: 1
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 64
        visible: opacity > 0
        opacity: toastTimer.running ? 1 : 0
        width: Math.min((parent ? parent.width : 400) - 40, toastContent.implicitWidth + 32)
        height: Math.max(44, toastContent.implicitHeight + 20)
        radius: Design.Theme.radiusMedium
        color: Design.Theme.surface
        border.width: 1
        border.color: Design.Theme.border

        Behavior on opacity {
            NumberAnimation {
                duration: toastTimer.running ? 160 : 100
                easing.type: toastTimer.running ? Easing.OutCubic : Easing.InCubic
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 4
            radius: 2
            color: root.toastStyle.color
        }

        Row {
            id: toastContent
            anchors.centerIn: parent
            spacing: Design.Theme.space2

            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: root.toastStyle.subtle

                Label {
                    anchors.centerIn: parent
                    text: root.toastStyle.glyph
                    color: root.toastStyle.color
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
            }

            Label {
                id: toastLabel
                width: Math.min(implicitWidth, (toast.parent ? toast.parent.width : 400) - 140)
                wrapMode: Text.Wrap
                text: root.toastText
                color: Design.Theme.textPrimary
            }
        }
    }
    Timer {
        id: toastTimer
        interval: 4000
        repeat: false
    }

    DetailedTextDialog {
        id: detailedDialog
        onSaved: (value) => root.saveDetailed(value)
    }

    AboutDialog {
        id: aboutDialog
        controller: root.controller
    }

    AiSettingsDialog {
        id: aiSettingsDialog
        controller: root.controller
        workspace: root
    }

    AppMessageDialog {
        id: messageDialog
    }

    AppMessageDialog {
        id: newCardDialog
        tone: "question"
        showCancel: true
        destructive: true
        onConfirmed: root.controller.requestNew()
    }

    AppMessageDialog {
        id: removeRecentDialog
        tone: "question"
        confirmText: "移除"
        showCancel: true
        destructive: true
        onConfirmed: root.controller.requestRemoveRecent(root.recentPendingRemoval)
    }

    PrtsQueryDialog {
        id: prtsDialog
        controller: root.controller
    }
}
