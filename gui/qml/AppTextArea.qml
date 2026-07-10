import QtQuick
import QtQuick.Controls

import "." as Design

TextArea {
    id: root

    property string value: ""
    property int debounceInterval: 280
    property bool hasError: false
    property string errorText: ""
    property string lastCommittedValue: ""
    signal valueCommitted(string value)

    font.family: Design.Theme.fontFamily
    font.pixelSize: Design.Theme.bodyFontSize
    color: Design.Theme.textPrimary
    selectByMouse: true
    wrapMode: TextArea.Wrap
    text: value
    leftPadding: Design.Theme.space3
    rightPadding: Design.Theme.space3
    topPadding: Design.Theme.space3
    bottomPadding: Design.Theme.space3

    function commitCurrent() {
        if (lastCommittedValue === text)
            return
        lastCommittedValue = text
        valueCommitted(text)
    }

    onValueChanged: lastCommittedValue = value
    onTextChanged: {
        if (activeFocus && debounceInterval > 0)
            commitTimer.restart()
    }
    onEditingFinished: {
        commitTimer.stop()
        commitCurrent()
    }

    Timer {
        id: commitTimer
        interval: root.debounceInterval
        repeat: false
        onTriggered: root.commitCurrent()
    }

    background: Rectangle {
        radius: Design.Theme.radiusSmall
        color: !root.enabled ? Design.Theme.disabledSurface
               : root.hovered || root.activeFocus
                 ? Design.Theme.surface : Design.Theme.fieldSurface
        border.width: 1
        border.color: root.hasError ? Design.Theme.danger
                      : root.activeFocus ? Design.Theme.focusBorder : Design.Theme.border

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 2
            radius: 1
            color: root.hasError ? Design.Theme.danger : Design.Theme.accent
            opacity: root.activeFocus || root.hasError ? 1 : 0

            Behavior on opacity {
                NumberAnimation { duration: 120 }
            }
        }
    }

    ToolTip.visible: root.hasError && root.hovered
    ToolTip.text: root.errorText
}
