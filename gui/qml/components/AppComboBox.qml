pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

ColumnLayout {
    id: root

    property var options: []
    property string value: ""
    property bool hasError: false
    property string errorText: ""
    property string placeholderText: "请选择"
    property bool showFocusFrame: true
    readonly property var effectiveOptions: {
        var result = options.slice()
        if (value.length > 0 && optionIndex(result, value) < 0) {
            result.push({
                value: value,
                label: value,
                legacy: true
            })
        }
        return result
    }
    signal valueCommitted(string value)

    spacing: Design.Theme.space1

    function optionIndex(items, targetValue) {
        for (var index = 0; index < items.length; ++index) {
            if (items[index].value === targetValue)
                return index
        }
        return -1
    }

    function currentLabel() {
        var index = optionIndex(effectiveOptions, value)
        return index >= 0 ? effectiveOptions[index].label : placeholderText
    }

    function syncCurrentIndex() {
        combo.currentIndex = optionIndex(effectiveOptions, value)
    }

    function syncHighlightedIndex() {
        var selectedIndex = optionIndex(effectiveOptions, value)
        optionList.currentIndex = selectedIndex >= 0 ? selectedIndex
                                                     : (effectiveOptions.length > 0 ? 0 : -1)
        if (optionList.currentIndex >= 0)
            optionList.positionViewAtIndex(optionList.currentIndex, ListView.Contain)
    }

    function selectOption(option) {
        if (!option)
            return
        valueCommitted(option.value)
        combo.popup.close()
        combo.forceActiveFocus()
    }

    function selectHighlighted() {
        if (optionList.currentIndex >= 0
                && optionList.currentIndex < effectiveOptions.length)
            selectOption(effectiveOptions[optionList.currentIndex])
    }

    function moveHighlight(step) {
        if (effectiveOptions.length === 0)
            return
        var nextIndex = optionList.currentIndex + step
        optionList.currentIndex = Math.max(0, Math.min(effectiveOptions.length - 1,
                                                       nextIndex))
        optionList.positionViewAtIndex(optionList.currentIndex, ListView.Contain)
    }

    onValueChanged: syncCurrentIndex()
    onEffectiveOptionsChanged: syncCurrentIndex()

    Connections {
        target: Design.Theme
        function onLightDismiss() {
            comboPopup.close()
        }
    }

    ComboBox {
        id: combo

        Layout.fillWidth: true
        model: root.effectiveOptions
        textRole: "label"
        valueRole: "value"
        currentIndex: -1
        implicitHeight: Design.Theme.controlHeight
        font.family: Design.Theme.fontFamily
        font.pixelSize: Design.Theme.bodyFontSize
        leftPadding: Design.Theme.space3
        rightPadding: Design.Theme.controlHeight
        wheelEnabled: false
        displayText: root.currentLabel()
        Component.onCompleted: root.syncCurrentIndex()
        onActivated: function(index) {
            if (index >= 0 && index < root.effectiveOptions.length)
                root.valueCommitted(root.effectiveOptions[index].value)
        }

        Keys.onPressed: function(event) {
            if (!popup.visible) {
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                        || event.key === Qt.Key_Space || event.key === Qt.Key_F4
                        || (event.key === Qt.Key_Down
                            && (event.modifiers & Qt.AltModifier))) {
                    popup.open()
                    event.accepted = true
                }
                return
            }

            if (event.key === Qt.Key_Down) {
                root.moveHighlight(1)
                event.accepted = true
            } else if (event.key === Qt.Key_Up) {
                root.moveHighlight(-1)
                event.accepted = true
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                       || event.key === Qt.Key_Space) {
                root.selectHighlighted()
                event.accepted = true
            } else if (event.key === Qt.Key_Escape) {
                popup.close()
                event.accepted = true
            }
        }

        contentItem: Label {
            text: combo.displayText
            color: !root.enabled ? Design.Theme.disabledText
                   : root.value.length === 0 ? Design.Theme.textSecondary
                                             : Design.Theme.textPrimary
            font: combo.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        indicator: Item {
            x: combo.width - width - Design.Theme.space2
            y: (combo.height - height) / 2
            width: Design.Theme.iconSize
            height: Design.Theme.iconSize
            rotation: combo.popup.visible ? 180 : 0

            Behavior on rotation {
                NumberAnimation {
                    duration: 140
                    easing.type: Easing.OutCubic
                }
            }

            Label {
                anchors.centerIn: parent
                text: "⌄"
                color: !root.enabled ? Design.Theme.disabledText
                       : combo.popup.visible || combo.visualFocus
                         ? Design.Theme.textPrimary : Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
            }
        }

        background: Rectangle {
            readonly property bool emphasized: combo.popup.visible || combo.visualFocus

            radius: Design.Theme.radiusMedium
            color: !root.enabled ? Design.Theme.disabledSurface
                   : emphasized || combo.hovered ? Design.Theme.surface
                                                 : Design.Theme.fieldSurface
            border.width: 1
            border.color: root.hasError ? Design.Theme.danger
                          : emphasized ? Design.Theme.borderStrong
                          : combo.hovered ? Design.Theme.borderHover
                          : Design.Theme.border

            Design.AppFocusFrame {
                active: root.showFocusFrame
                        && (combo.popup.visible || combo.visualFocus)
                hasError: root.hasError
            }
        }

        popup: Popup {
            id: comboPopup

            x: 0
            y: combo.height + Design.Theme.space1
            width: combo.width
            padding: Design.Theme.space2
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

            onAboutToShow: root.syncHighlightedIndex()
            onClosed: combo.forceActiveFocus()

            contentItem: ListView {
                id: optionList

                implicitHeight: Math.min(contentHeight, Design.Theme.comboPopupMaxHeight)
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                keyNavigationEnabled: false
                currentIndex: -1
                model: root.effectiveOptions
                spacing: 2
                reuseItems: true

                ScrollBar.vertical: ScrollBar {
                    readonly property bool hasOverflow:
                        optionList.contentHeight > optionList.height + 1

                    policy: hasOverflow ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                    active: hasOverflow
                }

                delegate: ItemDelegate {
                    id: optionDelegate

                    required property var modelData
                    required property int index

                    width: optionList.width
                    height: Design.Theme.comboOptionHeight
                    hoverEnabled: true
                    highlighted: optionList.currentIndex === optionDelegate.index
                    onHoveredChanged: {
                        if (hovered)
                            optionList.currentIndex = optionDelegate.index
                    }
                    onClicked: root.selectOption(optionDelegate.modelData)

                    contentItem: RowLayout {
                        spacing: Design.Theme.space2

                        Rectangle {
                            Layout.preferredWidth: 3
                            Layout.preferredHeight: 18
                            radius: 2
                            color: optionDelegate.modelData.legacy ? Design.Theme.warning
                                                                   : Design.Theme.accent
                            opacity: optionDelegate.modelData.value === root.value ? 1 : 0
                        }

                        Label {
                            Layout.fillWidth: true
                            text: optionDelegate.modelData.label
                            color: optionDelegate.modelData.legacy ? Design.Theme.warning
                                                                   : Design.Theme.textPrimary
                            font.family: Design.Theme.fontFamily
                            font.pixelSize: Design.Theme.bodyFontSize
                            font.weight: optionDelegate.modelData.value === root.value
                                         ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.preferredWidth: 16
                            text: "✓"
                            opacity: optionDelegate.modelData.value === root.value ? 1 : 0
                            color: optionDelegate.modelData.legacy ? Design.Theme.warning
                                                                   : Design.Theme.accent
                            font.family: Design.Theme.fontFamily
                            font.pixelSize: Design.Theme.bodyFontSize
                            font.weight: Font.DemiBold
                        }
                    }

                    background: Rectangle {
                        radius: Design.Theme.radiusSmall
                        color: {
                            var selected = optionDelegate.modelData.value === root.value
                            if (optionDelegate.down)
                                return Design.Theme.controlPressed
                            if (selected && (optionDelegate.hovered
                                             || optionDelegate.highlighted))
                                return Design.Theme.optionSelectedHover
                            if (selected)
                                return Design.Theme.optionSelected
                            if (optionDelegate.hovered || optionDelegate.highlighted)
                                return Design.Theme.optionHover
                            return "transparent"
                        }
                    }
                }
            }

            background: Rectangle {
                radius: Design.Theme.radiusMedium
                color: Design.Theme.popupSurface
                border.width: 1
                border.color: Design.Theme.border
            }

            enter: Transition {
                OpacityAnimator {
                    from: 0
                    to: 1
                    duration: 90
                }
            }

            exit: Transition {
                OpacityAnimator {
                    from: 1
                    to: 0
                    duration: 70
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
