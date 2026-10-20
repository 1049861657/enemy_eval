import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

ColumnLayout {
    id: root

    property string value: ""
    property int debounceInterval: 260
    property bool hasError: false
    property string errorText: ""
    property bool showClearButton: true
    property bool showFocusFrame: true
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

    function clearCurrent() {
        commitTimer.stop()
        editor.text = ""
        lastCommittedValue = ""
        valueCommitted("")
        editor.forceActiveFocus()
    }

    onValueChanged: {
        lastCommittedValue = value
        if (!editor.activeFocus && editor.text !== value)
            editor.text = value
    }
    Component.onCompleted: {
        lastCommittedValue = value
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
        placeholderTextColor: Design.Theme.textPlaceholder
        leftPadding: Design.Theme.space3
        rightPadding: clearButton.visible ? Design.Theme.controlHeight : Design.Theme.space3

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
            radius: Design.Theme.radiusMedium
            color: !root.enabled ? Design.Theme.disabledSurface
                   : editor.hovered || editor.activeFocus
                     ? Design.Theme.surface : Design.Theme.fieldSurface
            border.width: 1
            border.color: root.hasError ? Design.Theme.danger
                          : editor.activeFocus ? Design.Theme.borderStrong
                          : editor.hovered ? Design.Theme.borderHover
                          : Design.Theme.border

            Design.AppFocusFrame {
                active: root.showFocusFrame && editor.activeFocus
                hasError: root.hasError
            }
        }

        Item {
            id: clearButton

            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 32
            height: 32
            z: 2
            visible: root.showClearButton && editor.activeFocus
                     && editor.text.length > 0 && root.enabled
            ToolTip.visible: clearHover.hovered
            ToolTip.text: "清空输入"

            Rectangle {
                anchors.fill: parent
                radius: Design.Theme.radiusSmall
                color: clearTap.pressed ? Design.Theme.controlPressed
                       : clearHover.hovered ? Design.Theme.controlHover
                                            : "transparent"
            }

            Label {
                anchors.centerIn: parent
                text: "×"
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 16
            }

            HoverHandler {
                id: clearHover
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                id: clearTap
                onTapped: root.clearCurrent()
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
            Layout.preferredWidth: 14
            Layout.preferredHeight: 14
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
