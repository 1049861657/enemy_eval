import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    property string dialogTitle: ""
    property string message: ""
    property string tone: "info"
    property string confirmText: "知道了"
    property string cancelText: "取消"
    property bool showCancel: false
    property bool destructive: false
    signal confirmed()

    function show(title, body, dialogTone) {
        dialogTitle = title
        message = body
        tone = dialogTone || "info"
        open()
    }

    function toneColor() {
        if (tone === "error")
            return Design.Theme.danger
        if (tone === "warning" || tone === "question")
            return Design.Theme.warning
        if (tone === "success")
            return Design.Theme.success
        return Design.Theme.accent
    }

    function toneSymbol() {
        if (tone === "error")
            return "×"
        if (tone === "warning")
            return "!"
        if (tone === "question")
            return "?"
        if (tone === "success")
            return "✓"
        return "i"
    }

    function toneBackground() {
        if (tone === "error")
            return Design.Theme.dangerSubtle
        if (tone === "warning" || tone === "question")
            return Design.Theme.warningSubtle
        if (tone === "success")
            return Design.Theme.successSubtle
        return Design.Theme.accentSubtle
    }

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

    enter: Transition {
        NumberAnimation {
            property: "opacity"
            from: 0
            to: 1
            duration: 160
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            property: "scale"
            from: 0.965
            to: 1
            duration: 180
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
        NumberAnimation {
            property: "scale"
            from: 1
            to: 0.985
            duration: 90
            easing.type: Easing.InCubic
        }
    }

    onOpened: {
        if (root.destructive && root.showCancel)
            cancelButton.forceActiveFocus()
        else
            confirmButton.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space5

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: Design.Theme.space4

            Rectangle {
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                radius: 10
                color: root.toneBackground()

                Label {
                    anchors.centerIn: parent
                    text: root.toneSymbol()
                    color: root.toneColor()
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: 20
                    font.weight: Font.Bold
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Design.Theme.space2

                Label {
                    Layout.fillWidth: true
                    text: root.dialogTitle
                    color: Design.Theme.textPrimary
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.message
                    color: Design.Theme.textSecondary
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize
                    lineHeight: 1.35
                    wrapMode: Text.Wrap
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Item { Layout.fillWidth: true }

            AppButton {
                id: cancelButton
                visible: root.showCancel
                text: root.cancelText
                appearance: "secondary"
                onClicked: root.reject()
            }

            AppButton {
                id: confirmButton
                text: root.confirmText
                destructive: root.destructive
                onClicked: {
                    root.confirmed()
                    root.accept()
                }
            }
        }
    }
}
