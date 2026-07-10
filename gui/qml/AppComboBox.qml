import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

ColumnLayout {
    id: root

    property var options: []
    property string value: ""
    property bool hasError: false
    property string errorText: ""
    signal valueCommitted(string value)

    spacing: Design.Theme.space1

    ComboBox {
        id: combo

        Layout.fillWidth: true
        model: root.options.indexOf(root.value) >= 0 || root.value.length === 0
               ? root.options : root.options.concat([root.value])
        currentIndex: root.value.length === 0 ? 0 : model.indexOf(root.value)
        implicitHeight: Design.Theme.controlHeight
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.bodyFontSize
        onActivated: root.valueCommitted(currentText)

        background: Rectangle {
            radius: 6
            color: !root.enabled ? Design.Theme.disabledSurface
                   : combo.hovered || combo.activeFocus
                     ? Design.Theme.surface : Design.Theme.fieldSurface
            border.width: 1
            border.color: root.hasError ? Design.Theme.danger
                          : combo.activeFocus ? Design.Theme.borderStrong
                          : combo.hovered ? Design.Theme.borderHover
                          : Design.Theme.border

            Behavior on color {
                ColorAnimation { duration: 90 }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 2
                radius: 1
                color: root.hasError ? Design.Theme.danger : Design.Theme.accent
                opacity: combo.activeFocus || root.hasError ? 1 : 0

                Behavior on opacity {
                    NumberAnimation { duration: 120 }
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        visible: root.hasError && root.errorText.length > 0
        spacing: Design.Theme.space1

        Rectangle {
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: 3
            width: 14
            height: 14
            radius: 7
            color: Design.Theme.danger

            Label {
                anchors.centerIn: parent
                text: "!"
                color: "white"
                font.pixelSize: 10
                font.weight: Font.Bold
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.errorText
            color: Design.Theme.danger
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.captionFontSize
            wrapMode: Text.Wrap
        }
    }
}
