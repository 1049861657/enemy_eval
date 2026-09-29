pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Item {
    id: root

    required property var controller

    property var enemyData: ({})
    property var ratingNames: []
    property var recentFiles: []
    property bool schemaEditMode: false
    property var schemaDraft: []
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

    function refreshRatingNames(serialized) {
        ratingNames = JSON.parse(serialized)
    }

    function refreshRecentFiles(serialized) {
        recentFiles = JSON.parse(serialized)
    }

    function commit(field, value) {
        root.controller.updateProperty(field, JSON.stringify(value))
    }

    function commitAttackType(value) {
        commit("attack_type", value)
        if (value === "近战" || value === "不攻击")
            commit("attack_range_radius", 0)
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
        toastTimer.restart()
    }

    function confirmNewCard(isReset) {
        newCardDialog.dialogTitle = isReset
                ? "恢复默认数据？"
                : "丢弃当前内容并新建？"
        newCardDialog.message = isReset
                ? "当前编辑内容将被默认数据替换，且无法撤销。"
                : "所有未保存的修改都将丢失，且无法撤销。"
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

    function saveDetailed(value) {
        if (detailedTarget === "skillEffect")
            root.controller.skills.updateField(detailedSkillIndex, "效果", value)
        else
            commit(detailedTarget, value)
    }

    Component.onCompleted: {
        refreshData(root.controller.enemyDataJson, true)
        refreshRatingNames(root.controller.ratingNamesJson)
        refreshRecentFiles(root.controller.recentFilesJson)
    }

    Connections {
        target: root.controller
        function onEnemyDataChanged(serialized) { root.refreshData(serialized, true) }
        function onRatingNamesChanged(serialized) { root.refreshRatingNames(serialized) }
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
    }

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
            Layout.fillWidth: true
            workspace: root
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
                    onExportRequested: root.controller.requestExport()
                }
            }
        }
    }

    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 64
        visible: opacity > 0
        opacity: toastTimer.running ? 1 : 0
        width: Math.min(parent.width - 40, toastContent.implicitWidth + 32)
        height: Math.max(44, toastContent.implicitHeight + 20)
        radius: Design.Theme.radiusMedium
        color: Design.Theme.surface
        border.width: 1
        border.color: Design.Theme.border
        z: 20

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
                width: Math.min(implicitWidth, root.width - 100)
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
