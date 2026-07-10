import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

ColumnLayout {
    id: root

    property string value: ""
    property int debounceInterval: 260
    property bool hasError: false
    property string errorText: ""
    property bool showClearButton: true
    property bool stepKeysEnabled: false
    property string lastCommittedValue: ""
    property alias text: editor.text
    property alias placeholderText: editor.placeholderText
    property alias maximumLength: editor.maximumLength
    property alias inputMethodHints: editor.inputMethodHints
    signal valueCommitted(string value)
    signal editingFinished()
    signal accepted()
    signal stepRequested(int direction)

    spacing: Design.Theme.space1
    implicitHeight: editor.implicitHeight
                    + (feedback.visible ? feedback.implicitHeight + spacing : 0)

    function commitCurrent() {
        if (lastCommittedValue === editor.text)
            return
        lastCommittedValue = editor.text
        valueCommitted(editor.text)
    }

    function focusInput(selectExisting) {
        editor.forceActiveFocus()
        if (selectExisting)
            editor.selectAll()
    }

    onValueChanged: {
        lastCommittedValue = value
        if (!editor.activeFocus && editor.text !== value)
            editor.text = value
    }

    TextField {
        id: editor

        Layout.fillWidth: true
        implicitHeight: Design.Theme.controlHeight
        selectByMouse: true
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.bodyFontSize
        color: root.enabled ? Design.Theme.textPrimary : Design.Theme.disabledText
        placeholderTextColor: Design.Theme.textSecondary
        leftPadding: Design.Theme.space3
        rightPadding: clearButton.visible ? Design.Theme.controlHeight : Design.Theme.space3
        text: root.value

        onTextEdited: {
            if (root.debounceInterval > 0)
                commitTimer.restart()
        }
        onEditingFinished: {
            commitTimer.stop()
            root.commitCurrent()
            root.editingFinished()
        }
        onAccepted: {
            commitTimer.stop()
            root.commitCurrent()
            root.accepted()
        }

        Keys.onEscapePressed: function(event) {
            commitTimer.stop()
            editor.text = root.lastCommittedValue
            editor.selectAll()
            event.accepted = true
        }
        Keys.onUpPressed: function(event) {
            if (!root.stepKeysEnabled) {
                event.accepted = false
                return
            }
            root.stepRequested(1)
            event.accepted = true
        }
        Keys.onDownPressed: function(event) {
            if (!root.stepKeysEnabled) {
                event.accepted = false
                return
            }
            root.stepRequested(-1)
            event.accepted = true
        }

        background: Rectangle {
            radius: 6
            color: !root.enabled ? Design.Theme.disabledSurface
                   : editor.hovered || editor.activeFocus
                     ? Design.Theme.surface : Design.Theme.fieldSurface
            border.width: 1
            border.color: root.hasError ? Design.Theme.danger
                          : editor.activeFocus ? Design.Theme.borderStrong
                          : editor.hovered ? Design.Theme.borderHover
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
                opacity: editor.activeFocus || root.hasError ? 1 : 0

                Behavior on opacity {
                    NumberAnimation { duration: 120 }
                }
            }
        }

        AppIconButton {
            id: clearButton

            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 32
            height: 32
            visible: root.showClearButton && editor.activeFocus
                     && editor.text.length > 0 && root.enabled
            icon.source: "icons/close.svg"
            icon.width: 16
            icon.height: 16
            display: AbstractButton.IconOnly
            accessibleName: "清空输入"
            onClicked: {
                editor.clear()
                root.commitCurrent()
                editor.forceActiveFocus()
            }
        }
    }

    Timer {
        id: commitTimer
        interval: root.debounceInterval
        repeat: false
        onTriggered: root.commitCurrent()
    }

    RowLayout {
        id: feedback

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
            Accessible.role: Accessible.StaticText
        }
    }
}
