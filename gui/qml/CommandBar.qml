pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

ToolBar {
    id: root

    required property var workspace

    implicitHeight: 52
    padding: Design.Theme.space2

    component HistoryHalf: Item {
        id: half

        required property bool available
        required property url iconSource
        required property string tip
        required property string accessibleName
        property bool leading: true

        signal triggered()

        ToolTip.visible: hover.hovered
        ToolTip.text: half.tip
        ToolTip.delay: 600

        ToolButton {
            id: button

            anchors.fill: parent
            padding: 0
            leftPadding: 0
            rightPadding: 0
            topPadding: 0
            bottomPadding: 0
            display: AbstractButton.IconOnly
            icon.source: half.iconSource
            icon.width: 18
            icon.height: 18
            icon.color: half.available ? Design.Theme.textPrimary : Design.Theme.borderStrong
            opacity: half.available ? 1 : 0.72
            Accessible.name: half.accessibleName
            onClicked: {
                if (half.available)
                    half.triggered()
            }

            HoverHandler {
                id: hover
                cursorShape: half.available ? Qt.PointingHandCursor : Qt.ArrowCursor
            }

            background: Rectangle {
                color: half.available && button.down
                       ? Design.Theme.controlPressed
                       : "transparent"
                topLeftRadius: half.leading ? Design.Theme.radiusMedium : 0
                bottomLeftRadius: half.leading ? Design.Theme.radiusMedium : 0
                topRightRadius: half.leading ? 0 : Design.Theme.radiusMedium
                bottomRightRadius: half.leading ? 0 : Design.Theme.radiusMedium

                Design.AppFocusFrame {
                    active: button.visualFocus
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: Design.Theme.space2

        AppButton {
            text: "新建"
            iconSource: "icons/new.svg"
            onClicked: root.workspace.confirmNewCard(false)
        }
        AppButton {
            id: openButton
            text: "打开"
            iconSource: "icons/open.svg"
            dropdown: root.workspace.recentFiles.length > 0
            onClicked: {
                recentMenu.close()
                root.workspace.controller.requestOpen()
            }
            onDropdownClicked: recentMenu.toggle()

            Connections {
                target: root.workspace
                function onRecentFilesChanged() {
                    if (root.workspace.recentFiles.length === 0)
                        recentMenu.close()
                }
            }

            AppMenu {
                id: recentMenu
                y: openButton.height

                Instantiator {
                    model: root.workspace.recentFiles
                    delegate: MenuItem {
                        id: recentItem

                        required property var modelData

                        text: recentItem.modelData.name
                        icon.source: recentItem.modelData.exists ? "" : "icons/ban.svg"
                        icon.color: Design.Theme.warning
                        icon.width: 14
                        icon.height: 14
                        palette.text: recentItem.modelData.exists
                                      ? Design.Theme.textPrimary : Design.Theme.warning
                        rightPadding: Design.Theme.space5 + Design.Theme.space2
                        onTriggered: {
                            recentMenu.close()
                            if (recentItem.modelData.exists)
                                root.workspace.controller.requestOpenRecent(recentItem.modelData.path)
                            else
                                root.workspace.confirmRemoveRecent(recentItem.modelData.path,
                                                                   recentItem.modelData.name)
                        }

                        ToolTip.visible: recentItem.hovered
                        ToolTip.text: recentItem.modelData.path
                        ToolTip.delay: 600

                        ToolButton {
                            anchors.right: parent.right
                            anchors.rightMargin: Design.Theme.space1
                            anchors.verticalCenter: parent.verticalCenter
                            implicitWidth: Design.Theme.space5
                            implicitHeight: Design.Theme.space5
                            leftPadding: 0
                            rightPadding: 0
                            topPadding: 0
                            bottomPadding: 0
                            opacity: recentItem.hovered ? 1 : 0
                            display: AbstractButton.IconOnly
                            icon.source: "icons/delete.svg"
                            icon.color: Design.Theme.danger
                            icon.width: 16
                            icon.height: 16
                            onClicked: {
                                root.workspace.controller.requestRemoveRecent(recentItem.modelData.path)
                                recentMenu.close()
                            }
                        }
                    }
                    onObjectAdded: function (index, object) { recentMenu.insertItem(index, object) }
                    onObjectRemoved: function (index, object) { recentMenu.removeItem(object) }
                }

                MenuSeparator {}
                MenuItem {
                    text: "清除最近记录"
                    onTriggered: {
                        root.workspace.controller.requestClearRecent()
                        recentMenu.close()
                    }
                }
            }
        }
        AppButton {
            text: "保存"
            iconSource: "icons/save.svg"
            onClicked: root.workspace.controller.requestSave()
        }
        AppButton {
            text: "参考 PRTS"
            appearance: "secondary"
            enabled: !root.workspace.controller.prtsBusy
            onClicked: root.workspace.openPrtsDialog()
        }
        AppButton {
            id: moreButton
            text: "更多"
            appearance: "subtle"
            onClicked: commandMenu.toggle()

            AppMenu {
                id: commandMenu
                y: moreButton.height
                MenuItem { text: "刷新预览\tF5"; onTriggered: root.workspace.controller.requestRefresh() }
                MenuItem { text: "重置数据"; onTriggered: root.workspace.confirmNewCard(true) }
                MenuSeparator {}
                MenuItem { text: "检查更新"; onTriggered: root.workspace.controller.requestCheckUpdates() }
                MenuItem { text: "关于"; onTriggered: root.workspace.controller.requestAbout() }
                MenuItem { text: "退出\tCtrl+Q"; onTriggered: root.workspace.controller.requestQuit() }
            }
        }

        Rectangle {
            id: historyCapsule

            implicitWidth: Design.Theme.controlHeight * 2 + 1
            implicitHeight: Design.Theme.controlHeight
            radius: Design.Theme.radiusMedium
            color: Design.Theme.surfaceSubtle
            border.width: 1
            border.color: Design.Theme.border

            Row {
                anchors.fill: parent
                spacing: 0

                HistoryHalf {
                    width: (historyCapsule.width - 1) / 2
                    height: historyCapsule.height
                    available: root.workspace.controller.canUndo
                    iconSource: "icons/undo.svg"
                    tip: "撤销　Ctrl+Z"
                    accessibleName: "撤销"
                    leading: true
                    onTriggered: root.workspace.controller.requestUndo()
                }
                Item {
                    width: 1
                    height: parent.height

                    Rectangle {
                        anchors.centerIn: parent
                        width: 1
                        height: parent.height - Design.Theme.space3
                        color: Design.Theme.border
                    }
                }
                HistoryHalf {
                    width: (historyCapsule.width - 1) / 2
                    height: historyCapsule.height
                    available: root.workspace.controller.canRedo
                    iconSource: "icons/redo.svg"
                    tip: "重做　Ctrl+Y"
                    accessibleName: "重做"
                    leading: false
                    onTriggered: root.workspace.controller.requestRedo()
                }
            }
        }
        Item { Layout.fillWidth: true }
    }
}
