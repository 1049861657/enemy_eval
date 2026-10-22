import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import ".." as Design

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
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space3

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Image {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 192
                Layout.preferredHeight: 192
                Layout.bottomMargin: Design.Theme.space3
                source: root.controller.appIconUrl
                sourceSize.width: 384
                sourceSize.height: 384
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
            }

            Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.controller.appName
                wrapMode: Text.Wrap
                font.family: Design.Theme.fontFamily
                font.pixelSize: 24
                font.weight: Font.DemiBold
                color: Design.Theme.textPrimary
            }

            Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.controller.appSummary
                wrapMode: Text.Wrap
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
                color: Design.Theme.textSecondary
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: Design.Theme.space2
                spacing: Design.Theme.space2

                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: versionLabel.implicitWidth + Design.Theme.space4
                    implicitHeight: versionLabel.implicitHeight + Design.Theme.space2
                    radius: height / 2
                    color: Design.Theme.surfaceSubtle

                    Label {
                        id: versionLabel
                        anchors.centerIn: parent
                        text: root.controller.appVersion
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                        color: Design.Theme.textSecondary
                    }
                }

                AppButton {
                    text: "检查更新"
                    appearance: "secondary"
                    onClicked: root.controller.requestCheckUpdates()
                }
            }

            Label {
                Layout.fillWidth: true
                visible: root.controller.appBuildTime !== ""
                horizontalAlignment: Text.AlignHCenter
                text: "构建于 " + root.controller.appBuildTime
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
                color: Design.Theme.textSecondary
            }

            Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: "字体：HarmonyOS Sans"
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
                color: Design.Theme.textSecondary
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: Design.Theme.space3
            implicitWidth: updateRow.implicitWidth
            implicitHeight: updateRow.implicitHeight + Design.Theme.space3 * 2
            radius: Design.Theme.radiusLarge
            color: Design.Theme.surfaceSubtle

            RowLayout {
                id: updateRow
                x: Design.Theme.space4
                y: Design.Theme.space3
                width: parent.width - Design.Theme.space4 * 2
                spacing: Design.Theme.space3

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        Layout.fillWidth: true
                        text: "启动时检查更新"
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.bodyFontSize
                        color: Design.Theme.textPrimary
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "有新版本时，启动后提示"
                        wrapMode: Text.Wrap
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                        color: Design.Theme.textSecondary
                    }
                }

                Switch {
                    id: autoCheck
                    Layout.alignment: Qt.AlignVCenter
                    checked: root.controller.updateCheckEnabled
                    onCheckedChanged: {
                        if (checked !== root.controller.updateCheckEnabled)
                            root.controller.setUpdateCheckEnabled(checked)
                    }
                }
            }
        }

        AppButton {
            Layout.alignment: Qt.AlignRight
            Layout.topMargin: Design.Theme.space2
            text: "知道了"
            appearance: "secondary"
            onClicked: root.close()
        }
    }
}
