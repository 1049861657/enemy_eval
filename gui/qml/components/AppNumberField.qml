import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

RowLayout {
    id: root

    property real value: 0
    property real minimum: 0
    property real maximum: 999999
    property real stepSize: 1
    property int decimals: 0
    property bool hasError: false
    property string errorText: ""
    property bool inputInvalid: false
    signal valueCommitted(real value)

    function format(value) {
        return decimals > 0 ? Number(value).toFixed(decimals) : String(Math.round(value))
    }

    function commitText() {
        var parsed = Number(editor.text)
        if (!Number.isFinite(parsed) || parsed < minimum || parsed > maximum) {
            inputInvalid = true
            editor.lastCommittedValue = format(value)
            return
        }
        inputInvalid = false
        valueCommitted(parsed)
    }

    function adjustValue(direction) {
        inputInvalid = false
        var adjusted = value + direction * stepSize
        valueCommitted(Math.max(minimum, Math.min(maximum, adjusted)))
    }

    onValueChanged: inputInvalid = false
    spacing: Design.Theme.space1

    AppTextField {
        id: editor
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        value: root.format(root.value)
        debounceInterval: 0
        showClearButton: false
        stepKeysEnabled: true
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        hasError: root.hasError || root.inputInvalid
        errorText: root.inputInvalid
                   ? "请输入 " + root.format(root.minimum) + "–" + root.format(root.maximum)
                   : root.errorText
        onValueCommitted: root.commitText()
        onStepRequested: (direction) => root.adjustValue(direction)
    }
    ToolButton {
        id: decrementButton

        text: "−"
        Layout.alignment: Qt.AlignTop
        implicitWidth: Design.Theme.controlHeight
        implicitHeight: Design.Theme.controlHeight
        autoRepeat: true
        autoRepeatDelay: 420
        autoRepeatInterval: 70
        ToolTip.visible: hovered
        ToolTip.text: "减少 " + root.stepSize
        enabled: root.enabled && root.value > root.minimum
        onClicked: root.adjustValue(-1)

        background: Rectangle {
            radius: Design.Theme.radiusMedium
            color: decrementButton.down ? Design.Theme.controlPressed
                  : decrementButton.hovered ? Design.Theme.controlHover
                  : Design.Theme.fieldSurface
            border.width: 1
            border.color: decrementButton.hovered
                          ? Design.Theme.borderHover : Design.Theme.border

            Design.AppFocusFrame {
                active: decrementButton.visualFocus
            }
        }
    }
    ToolButton {
        id: incrementButton

        text: "+"
        Layout.alignment: Qt.AlignTop
        implicitWidth: Design.Theme.controlHeight
        implicitHeight: Design.Theme.controlHeight
        autoRepeat: true
        autoRepeatDelay: 420
        autoRepeatInterval: 70
        ToolTip.visible: hovered
        ToolTip.text: "增加 " + root.stepSize
        enabled: root.enabled && root.value < root.maximum
        onClicked: root.adjustValue(1)

        background: Rectangle {
            radius: Design.Theme.radiusMedium
            color: incrementButton.down ? Design.Theme.controlPressed
                  : incrementButton.hovered ? Design.Theme.controlHover
                  : Design.Theme.fieldSurface
            border.width: 1
            border.color: incrementButton.hovered
                          ? Design.Theme.borderHover : Design.Theme.border

            Design.AppFocusFrame {
                active: incrementButton.visualFocus
            }
        }
    }
}
