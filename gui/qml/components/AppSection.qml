import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

Pane {
    id: root

    property string title: ""
    default property alias content: contentColumn.data
    property alias headerActions: headerActionsContainer.data
    property alias titleTrailing: titleTrailingContainer.data

    padding: Design.Theme.space4
    background: Rectangle {
        color: Design.Theme.surface
        border.color: "transparent"
        radius: Design.Theme.radiusMedium
    }

    contentItem: Column {
        id: contentColumn
        width: root.availableWidth
        spacing: Design.Theme.space3

        Item {
            id: sectionHeader

            width: parent.width
            height: Math.max(
                        titleLabel.implicitHeight,
                        headerActionsContainer.height,
                        titleTrailingContainer.height
                    ) + Design.Theme.space2
            visible: root.title.length > 0
                     || headerActionsContainer.children.length > 0
                     || titleTrailingContainer.children.length > 0

            RowLayout {
                id: headerRow

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: parent.height - Design.Theme.space2
                spacing: Design.Theme.space2

                Item {
                    Layout.preferredWidth: 4
                    Layout.fillHeight: true

                    Rectangle {
                        anchors.centerIn: parent
                        width: 3
                        height: 16
                        radius: 2
                        color: Design.Theme.accent
                    }
                }

                Label {
                    id: titleLabel

                    Layout.alignment: Qt.AlignVCenter
                    text: root.title
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize + 1
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.3
                    color: Design.Theme.textPrimary
                    verticalAlignment: Text.AlignVCenter
                }

                Row {
                    id: titleTrailingContainer

                    Layout.alignment: Qt.AlignVCenter
                    spacing: Design.Theme.space1
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }

                Row {
                    id: headerActionsContainer

                    Layout.alignment: Qt.AlignVCenter
                    spacing: Design.Theme.space1
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Design.Theme.border
                opacity: 0.55
            }
        }
    }
}
