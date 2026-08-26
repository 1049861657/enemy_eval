import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

ToolBar {
    id: root

    required property var workspace

    implicitHeight: 52
    padding: Design.Theme.space2

    RowLayout {
        anchors.fill: parent
        spacing: Design.Theme.space2

        AppButton {
            text: "新建"
            iconSource: "icons/new.svg"
            onClicked: root.workspace.confirmNewCard(false)
        }
        AppButton {
            text: "打开"
            iconSource: "icons/open.svg"
            onClicked: root.workspace.controller.requestOpen()
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
            onClicked: commandMenu.open()

            Menu {
                id: commandMenu
                y: moreButton.height
                MenuItem { text: "刷新预览\tF5"; onTriggered: root.workspace.controller.requestRefresh() }
                MenuItem { text: "重置数据"; onTriggered: root.workspace.confirmNewCard(true) }
                MenuSeparator {}
                MenuItem { text: "关于"; onTriggered: root.workspace.controller.requestAbout() }
                MenuItem { text: "退出\tCtrl+Q"; onTriggered: root.workspace.controller.requestQuit() }
            }
        }
        Item { Layout.fillWidth: true }
    }
}
