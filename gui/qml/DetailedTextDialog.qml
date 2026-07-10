import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    property string editorTitle: "详细编辑"
    property string initialValue: ""
    signal saved(string value)

    title: ""
    modal: true
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 80 : 800, 860)
    height: Math.min(parent ? parent.height - 80 : 600, 640)
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5

    Overlay.modal: Rectangle {
        color: Design.Theme.overlay
    }

    background: Rectangle {
        color: Design.Theme.surface
        radius: Design.Theme.radiusLarge
        border.width: 1
        border.color: Design.Theme.border
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: 140 }
    }

    function openFor(title, value) {
        editorTitle = title
        initialValue = value
        editor.text = value
        open()
    }

    onOpened: {
        editor.forceActiveFocus()
        editor.cursorPosition = editor.text.length
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space3

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.editorTitle
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.titleFontSize
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            Label {
                text: "Ctrl+Enter 保存"
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
            }
        }

        ScrollView {
            id: editorScroll

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            AppTextArea {
                id: editor

                width: editorScroll.availableWidth
                height: Math.max(
                    editorScroll.availableHeight,
                    contentHeight + topPadding + bottomPadding
                )
                debounceInterval: -1
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignTop
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: editor.text.length + " 字"
                color: Design.Theme.textSecondary
                Layout.fillWidth: true
            }
            AppButton {
                text: "取消"
                appearance: "secondary"
                onClicked: root.reject()
            }
            AppButton {
                text: "保存"
                onClicked: {
                    root.saved(editor.text)
                    root.accept()
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+Return"
        onActivated: {
            root.saved(editor.text)
            root.accept()
        }
    }
}
