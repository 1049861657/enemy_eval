import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

Pane {
    id: root

    property string title: ""
    property string helperText: ""
    property string placeholderText: ""
    property string value: ""
    property bool framed: true
    property bool hasError: false
    property string errorText: ""
    property bool showFocusFrame: false
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
        radius: Design.Theme.radiusMedium
        border.width: 0
    }

    contentItem: ColumnLayout {
        spacing: root.framed ? Design.Theme.space3 : Design.Theme.space2

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(titleLabel.implicitHeight, 40)
                                    + (root.framed ? Design.Theme.space2 : 0)

            RowLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: parent.height - (root.framed ? Design.Theme.space2 : 0)
                spacing: Design.Theme.space2

                Rectangle {
                    visible: root.framed
                    Layout.preferredWidth: visible ? 3 : 0
                    Layout.preferredHeight: 16
                    radius: 2
                    color: Design.Theme.accent
                }

                Label {
                    id: titleLabel

                    text: root.title
                    color: Design.Theme.textPrimary
                    font.family: Design.Theme.fontFamily
                    font.pixelSize: Design.Theme.bodyFontSize + (root.framed ? 1 : 0)
                    font.weight: Font.DemiBold
                    font.letterSpacing: root.framed ? 0.3 : 0
                    Layout.fillWidth: true
                }

                AppIconButton {
                    id: editButton

                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    icon.source: "../icons/edit.svg"
                    icon.width: 24
                    icon.height: 24
                    display: AbstractButton.IconOnly
                    ToolTip.visible: hovered
                    ToolTip.text: "编辑"
                    onClicked: root.expandRequested()
                }
            }

            Rectangle {
                visible: root.framed
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Design.Theme.border
                opacity: 0.55
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
                          : editor.activeFocus ? Design.Theme.borderStrong
                          : editor.hovered ? Design.Theme.borderHover
                          : Design.Theme.border

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
                    placeholderTextColor: Design.Theme.textPlaceholder
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

            Design.AppFocusFrame {
                active: root.showFocusFrame && editor.activeFocus
                hasError: root.hasError
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
