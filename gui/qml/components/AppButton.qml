import QtQuick
import QtQuick.Controls

import ".." as Design

Button {
    id: root

    property bool destructive: false
    property url iconSource: ""
    property string appearance: "primary"
    property bool dropdown: false
    property bool menu: false
    property bool active: false

    signal dropdownClicked()

    readonly property real dropdownZoneWidth: dropdown
                                               ? Math.round(Design.Theme.controlHeight * 0.8) : 0
    readonly property bool mainHovered: hovered && !(dropdown && dropdownButton.hovered)
    readonly property bool mainDown: down && !(dropdown && dropdownButton.pressed)

    implicitHeight: Design.Theme.controlHeight
    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding + dropdownZoneWidth
    padding: Design.Theme.space3
    scale: down ? 0.985 : 1
    font.family: Design.Theme.fontFamily
    font.pixelSize: Design.Theme.bodyFontSize
    icon.source: iconSource
    display: iconSource === "" ? AbstractButton.TextOnly : AbstractButton.TextBesideIcon

    Behavior on scale {
        NumberAnimation {
            duration: root.down ? 55 : 110
            easing.type: root.down ? Easing.InCubic : Easing.OutCubic
        }
    }

    background: Rectangle {
        radius: Design.Theme.radiusSmall
        color: !root.enabled ? Design.Theme.disabledSurface
              : root.appearance === "command" ? (root.mainDown || root.active
                                                 ? Design.Theme.controlPressed
                                                 : root.mainHovered ? Design.Theme.controlHover
                                                                    : "transparent")
              : root.appearance === "subtle" ? (root.mainDown || root.mainHovered
                                                 ? (root.destructive
                                                    ? Design.Theme.dangerSubtle
                                                    : Design.Theme.controlHover)
                                                 : "transparent")
              : root.appearance === "secondary" ? (root.mainDown ? (root.destructive
                                                                ? Design.Theme.dangerSubtle
                                                                : Design.Theme.controlPressed)
                                                 : root.mainHovered ? (root.destructive
                                                                   ? Design.Theme.dangerSubtle
                                                                   : Design.Theme.controlHover)
                                                                : Design.Theme.surface)
              : root.mainDown ? (root.destructive ? Design.Theme.dangerHover : Design.Theme.accentPressed)
              : root.mainHovered ? (root.destructive ? Design.Theme.dangerHover : Design.Theme.accentHover)
              : (root.destructive ? Design.Theme.danger : Design.Theme.accent)
        border.color: root.appearance === "secondary"
                      ? (root.destructive ? Design.Theme.danger : Design.Theme.border)
                      : "transparent"

        Design.AppFocusFrame {
            active: root.visualFocus
        }

        Rectangle {
            id: dropdownDivider
            visible: root.dropdown
            anchors.right: dropdownButton.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: Design.Theme.space2
            anchors.bottomMargin: Design.Theme.space2
            width: 1
            color: root.appearance === "primary"
                   ? Qt.rgba(1, 1, 1, 0.35) : Design.Theme.border
        }
    }
    contentItem: Item {
        implicitWidth: buttonContent.implicitWidth
        implicitHeight: buttonContent.implicitHeight

        Row {
            id: buttonContent
            spacing: root.menu
                     || (root.iconSource.toString().length > 0 && root.text.length > 0)
                     ? Design.Theme.space1 : 0
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: root.dropdown ? -root.dropdownZoneWidth / 2 : 0

            Image {
                visible: root.iconSource.toString().length > 0
                source: root.iconSource
                width: Design.Theme.iconSize
                height: Design.Theme.iconSize
                fillMode: Image.PreserveAspectFit
            }
            Text {
                visible: root.text.length > 0
                text: root.text
                color: !root.enabled ? Design.Theme.disabledText
                       : root.appearance === "primary" ? "white"
                       : root.destructive ? Design.Theme.danger : Design.Theme.textPrimary
                font: root.font
                verticalAlignment: Text.AlignVCenter
            }
            Text {
                visible: root.menu
                text: "▾"
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 11
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    ToolButton {
        id: dropdownButton
        z: 1
        visible: root.dropdown
        enabled: root.enabled
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.dropdownZoneWidth
        padding: 0
        onClicked: root.dropdownClicked()

        background: Rectangle {
            topRightRadius: Design.Theme.radiusSmall
            bottomRightRadius: Design.Theme.radiusSmall
            color: !root.enabled ? Design.Theme.disabledSurface
                   : dropdownButton.down
                     ? (root.appearance === "primary" ? Design.Theme.accentPressed
                        : root.destructive ? Design.Theme.dangerSubtle : Design.Theme.controlPressed)
                   : dropdownButton.hovered
                     ? (root.appearance === "primary" ? Design.Theme.accentHover
                        : root.destructive ? Design.Theme.dangerSubtle : Design.Theme.controlHover)
                   : "transparent"

            Design.AppFocusFrame {
                active: dropdownButton.visualFocus
            }
        }

        contentItem: Item {
            Image {
                anchors.centerIn: parent
                width: Math.round(Design.Theme.iconSize * 0.6)
                height: width
                source: "../icons/chevron_down.svg"
                fillMode: Image.PreserveAspectFit
            }
        }
    }
}
