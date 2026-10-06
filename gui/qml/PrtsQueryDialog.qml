import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    required property var controller

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 48 : 440, 440)
    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5
    onAccepted: root.controller.requestPrtsQuery(prtsName.text)
    onOpened: prtsName.focusInput(true)

    Overlay.modal: Rectangle {
        color: Design.Theme.overlay
    }

    background: Rectangle {
        color: Design.Theme.surface
        radius: Design.Theme.radiusLarge
        border.width: 1
        border.color: Design.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space4

        Label {
            text: "参考 PRTS"
            color: Design.Theme.textPrimary
            font.family: Design.Theme.fontFamily
            font.pixelSize: 18
            font.weight: Font.DemiBold
        }

        Label {
            Layout.fillWidth: true
            text: "输入PRTS的敌人准确名称，自动填入相关字段"
            color: Design.Theme.textSecondary
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
        }

        AppTextField {
            id: prtsName
            Layout.fillWidth: true
            placeholderText: "敌人名称"
            showFocusFrame: false
            onAccepted: {
                if (fetchPrtsButton.enabled)
                    root.accept()
            }
        }

        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: root.controller.prtsBusy
            visible: running
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Item { Layout.fillWidth: true }

            AppButton {
                text: "取消"
                appearance: "secondary"
                onClicked: root.reject()
            }

            AppButton {
                id: fetchPrtsButton
                text: "获取数据"
                enabled: prtsName.text.trim().length > 0 && !root.controller.prtsBusy
                onClicked: root.accept()
            }
        }
    }
}
