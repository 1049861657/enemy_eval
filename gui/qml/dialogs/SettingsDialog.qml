pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"
import ".." as Design

Dialog {
    id: root

    required property var controller
    required property var workspace

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width - 48 : 620, 620)
    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    padding: Design.Theme.space5

    property string section: "ai"

    readonly property string errorText: root.workspace.fieldErrors["ai_settings"] || ""
    readonly property string baseUrlPreview: root.controller.aiBaseUrlPreview(baseUrlField.text)

    component NavItem: ItemDelegate {
        id: navItem

        required property string sectionKey
        required property string label

        Layout.fillWidth: true
        implicitHeight: 34
        padding: 0
        onClicked: root.section = navItem.sectionKey

        contentItem: Label {
            leftPadding: Design.Theme.space2
            text: navItem.label
            color: root.section === navItem.sectionKey
                   ? Design.Theme.textPrimary : Design.Theme.textSecondary
            font.family: Design.Theme.fontFamily
            font.pixelSize: Design.Theme.bodyFontSize
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: Design.Theme.radiusSmall
            color: root.section === navItem.sectionKey
                   ? Design.Theme.controlPressed
                   : navItem.hovered ? Design.Theme.controlHover : "transparent"
        }
    }

    function resetAiFields() {
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

    function openAt(name) {
        root.section = name || "ai"
        root.resetAiFields()
        root.open()
    }

    function submitAi() {
        if (root.controller.saveAiSettings(
                    baseUrlField.text.trim(), modelField.text.trim(), keyField.text))
            root.workspace.clearFieldError("ai_settings")
    }

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

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space2

            Label {
                text: "设置"
                color: Design.Theme.textPrimary
                font.family: Design.Theme.fontFamily
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            Item { Layout.fillWidth: true }

            AppIconButton {
                icon.source: "../icons/close.svg"
                icon.width: Design.Theme.iconSize
                icon.height: Design.Theme.iconSize
                toolTipText: "关闭"
                Accessible.name: "关闭"
                onClicked: root.close()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Design.Theme.space4

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 118
                spacing: Design.Theme.space1

                NavItem { sectionKey: "ai"; label: "AI" }
                NavItem { sectionKey: "network"; label: "网络" }
            }

            Rectangle {
                Layout.fillHeight: true
                implicitWidth: 1
                color: Design.Theme.border
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                currentIndex: root.section === "network" ? 1 : 0

                ColumnLayout {
                    spacing: Design.Theme.space3

                    Label {
                        Layout.fillWidth: true
                        text: "填写后可供 AI 功能使用（连通性请自行保证）"
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
                            onAccepted: root.submitAi()
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
                            onAccepted: root.submitAi()
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
                            onAccepted: root.submitAi()
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: root.controller.aiConfigured
                              ? "当前配置：已配置"
                              : "当前配置：未配置（三项齐全后可用）"
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
                            text: "保存"
                            onClicked: root.submitAi()
                        }
                    }
                }

                ColumnLayout {
                    spacing: Design.Theme.space3

                    Label {
                        Layout.fillWidth: true
                        text: "代理方式决定全局如何访问网络。"
                        wrapMode: Text.Wrap
                        color: Design.Theme.textSecondary
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.bodyFontSize
                    }

                    AppComboBox {
                        Layout.fillWidth: true
                        options: [
                            { value: "none", label: "不使用代理" },
                            { value: "system", label: "跟随系统" }
                        ]
                        value: root.controller.proxyMode
                        onValueCommitted: (mode) => {
                            if (mode !== root.controller.proxyMode)
                                root.controller.setProxyMode(mode)
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "跟随系统时按环境变量或操作系统代理设置；不使用代理时全部直连。"
                        wrapMode: Text.Wrap
                        color: Design.Theme.textSecondary
                        font.family: Design.Theme.fontFamily
                        font.pixelSize: Design.Theme.captionFontSize
                    }
                }
            }
        }
    }
}
