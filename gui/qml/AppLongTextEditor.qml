import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Pane {
    id: root

    property string title: ""
    property string helperText: ""
    property string placeholderText: ""
    property string value: ""
    property bool framed: true
    property bool hasError: false
    property string errorText: ""
    property int editorHeight: 116
    property int debounceInterval: 320
    property string lastCommittedValue: ""
    signal valueCommitted(string value)
    signal expandRequested()

    padding: framed ? Design.Theme.space4 : 0

    function commitCurrent() {
        if (lastCommittedValue === editor.text)
            return
        lastCommittedValue = editor.text
        valueCommitted(editor.text)
    }

    onValueChanged: {
        lastCommittedValue = value
        if (!editor.activeFocus && editor.text !== value)
            editor.text = value
    }

    background: Rectangle {
        color: root.framed ? Design.Theme.surface : "transparent"
        radius: Design.Theme.radiusLarge
        border.width: root.framed ? 1 : 0
        border.color: Design.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space2

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Label {
                text: root.title
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            AppIconButton {
                icon.source: "icons/edit.svg"
                icon.width: Design.Theme.iconSize
                icon.height: Design.Theme.iconSize
                display: AbstractButton.IconOnly
                Accessible.name: "编辑" + root.title
                ToolTip.visible: hovered
                ToolTip.text: "编辑"
                onClicked: root.expandRequested()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.editorHeight
            radius: Design.Theme.radiusMedium
            color: editor.hovered || editor.activeFocus
                   ? Design.Theme.surface : Design.Theme.fieldSurface
            border.width: 1
            border.color: root.hasError ? Design.Theme.danger
                          : editor.activeFocus ? Design.Theme.focusBorder
                          : Design.Theme.border

            Behavior on color {
                ColorAnimation { duration: 90 }
            }

            ScrollView {
                id: editorScroll
                anchors.fill: parent
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                TextArea {
                    id: editor

                    width: editorScroll.availableWidth
                    height: Math.max(
                        editorScroll.availableHeight,
                        contentHeight + topPadding + bottomPadding
                    )
                    leftPadding: Design.Theme.space3
                    rightPadding: Design.Theme.space4
                    topPadding: Design.Theme.space3
                    bottomPadding: 30
                    background: null
                    text: root.value
                    placeholderText: root.placeholderText
                    color: Design.Theme.textPrimary
                    placeholderTextColor: Design.Theme.textSecondary
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize
                    selectByMouse: true
                    wrapMode: TextArea.Wrap
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignTop

                    onTextChanged: {
                        if (activeFocus)
                            commitTimer.restart()
                    }
                    onEditingFinished: {
                        commitTimer.stop()
                        root.commitCurrent()
                    }

                    Accessible.name: root.title
                    Accessible.description: root.helperText
                }
            }

            Label {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Design.Theme.space2
                text: editor.text.length + " 字"
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
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

        Label {
            Layout.fillWidth: true
            visible: root.hasError && root.errorText.length > 0
            text: root.errorText
            color: Design.Theme.danger
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.captionFontSize
            wrapMode: Text.Wrap
        }
    }

    Timer {
        id: commitTimer
        interval: root.debounceInterval
        repeat: false
        onTriggered: root.commitCurrent()
    }

}
