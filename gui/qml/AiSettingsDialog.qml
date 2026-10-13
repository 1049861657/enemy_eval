import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "." as Design

Dialog {
    id: root

    required property var controller
    required property var workspace

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 48 : 440, 440)
    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5

    readonly property string errorText: root.workspace.fieldErrors["ai_settings"] || ""
    readonly property string baseUrlPreview: root.controller.aiBaseUrlPreview(baseUrlField.text)

    function resetFields() {
        baseUrlField.value = root.controller.aiBaseUrl
        baseUrlField.text = root.controller.aiBaseUrl
        baseUrlField.lastCommittedValue = root.controller.aiBaseUrl
        modelField.value = root.controller.aiModel
        modelField.text = root.controller.aiModel
        modelField.lastCommittedValue = root.controller.aiModel
        keyField.value = root.controller.aiApiKey
        keyField.text = root.controller.aiApiKey
        keyField.lastCommittedValue = root.controller.aiApiKey
        root.workspace.clearFieldError("ai_settings")
    }

    function submit() {
        if (root.controller.saveAiSettings(
                    baseUrlField.text.trim(), modelField.text.trim(), keyField.text))
            root.close()
    }

    onOpened: root.resetFields()

    Overlay.modal: Rectangle {
        color: Design.Theme.overlay
    }

    background: Rectangle {
        color: Design.Theme.surface
        radius: Design.Theme.radiusLarge
        border.width: 1
        border.color: Design.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: Design.Theme.space4

        Label {
            text: "AI 设置"
            color: Design.Theme.textPrimary
            font.family: Design.Theme.fontFamily
            font.pixelSize: 18
            font.weight: Font.DemiBold
        }

        Label {
            Layout.fillWidth: true
            text: "填写后可使用 AI（连通性请自行保证）"
            wrapMode: Text.Wrap
            color: Design.Theme.textSecondary
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space1

            Label {
                text: "Base URL"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
            }

            AppTextField {
                id: baseUrlField
                Layout.fillWidth: true
                placeholderText: "https://api.deepseek.com/v1"
                hasError: root.errorText !== ""
                onAccepted: root.submit()
            }

            Label {
                Layout.fillWidth: true
                visible: root.baseUrlPreview !== ""
                text: "To " + root.baseUrlPreview
                wrapMode: Text.Wrap
                color: Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space1

            Label {
                text: "模型名"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
            }

            AppTextField {
                id: modelField
                Layout.fillWidth: true
                placeholderText: "deepseek-chat"
                hasError: root.errorText !== ""
                onAccepted: root.submit()
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space1

            Label {
                text: "密钥"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
            }

            AppTextField {
                id: keyField
                Layout.fillWidth: true
                placeholderText: "供应商控制台里生成的密钥"
                hasError: root.errorText !== ""
                onAccepted: root.submit()
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.controller.aiConfigured
                  ? "当前配置：已配置"
                  : "当前配置：未配置（三项齐全后才能评价）"
            wrapMode: Text.Wrap
            color: Design.Theme.textSecondary
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.captionFontSize
        }

        Label {
            Layout.fillWidth: true
            visible: root.errorText !== ""
            text: root.errorText
            wrapMode: Text.Wrap
            color: Design.Theme.danger
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.captionFontSize
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Item { Layout.fillWidth: true }

            AppButton {
                text: "取消"
                appearance: "secondary"
                onClicked: root.close()
            }

            AppButton {
                text: "保存"
                onClicked: root.submit()
            }
        }
    }
}
