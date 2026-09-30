import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    required property var controller

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 48 : 440, 460)
    modal: true
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5

    Overlay.modal: Rectangle {
        color: Design.Theme.overlay
    }

    background: Rectangle {
        color: Design.Theme.surface
        radius: 14
        border.width: 1
        border.color: Design.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space4

        Label {
            Layout.fillWidth: true
            text: "敌人评价卡片实时编辑器"
            wrapMode: Text.Wrap
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.titleFontSize
            font.weight: Font.Medium
            color: Design.Theme.textPrimary
        }

        Label {
            Layout.fillWidth: true
            text: "版本：" + root.controller.appVersion
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
            color: Design.Theme.textPrimary
        }

        Label {
            Layout.fillWidth: true
            visible: root.controller.appBuildTime !== ""
            text: "构建日期：" + root.controller.appBuildTime
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
            color: Design.Theme.textPrimary
        }

        Label {
            Layout.fillWidth: true
            text: "一个明日方舟的敌人评价卡片生成工具\n支持实时预览和属性编辑"
            wrapMode: Text.Wrap
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
            color: Design.Theme.textSecondary
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Design.Theme.space2
            spacing: Design.Theme.space3

            Label {
                Layout.fillWidth: true
                text: "启动时自动检查更新"
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
                color: Design.Theme.textPrimary
            }

            Switch {
                id: autoCheck
                checked: root.controller.updateCheckEnabled
                onCheckedChanged: {
                    if (checked !== root.controller.updateCheckEnabled)
                        root.controller.setUpdateCheckEnabled(checked)
                }
            }
        }

        AppButton {
            Layout.alignment: Qt.AlignRight
            text: "知道了"
            onClicked: root.close()
        }
    }
}
