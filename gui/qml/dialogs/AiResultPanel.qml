pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import ".." as Design

/** AI 简评结果区：建议正文（可编辑）、状态行、还原、空态骨架与进度条。
 *
 * 状态由父级持有：正文用 `text` 别名双向绑定，父级据此判定 `edited` / `canAdopt` 与采纳。
 */
Rectangle {
    id: root

    /** 建议正文；父级经别名读写（编辑框可改）。 */
    property alias text: suggestionArea.text

    /** 最近一次成功结果的副本；「还原」回到此值。 */
    property string suggestionText: ""
    /** 父级 `stateText()` 的结果（生成中秒数 / 已改动 / 字数）。 */
    property string stateText: ""
    property bool busy: false
    property bool hasResult: false
    property bool generating: false
    property bool configured: false
    property bool edited: false

    radius: Design.Theme.radiusMedium
    color: Design.Theme.surface
    border.width: 1
    border.color: suggestionArea.activeFocus ? Design.Theme.borderStrong
                  : root.hasResult ? Design.Theme.accent
                  : Design.Theme.border
    clip: true

    Behavior on border.color {
        ColorAnimation {
            duration: 160
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            Layout.leftMargin: Design.Theme.space4
            Layout.rightMargin: Design.Theme.space4
            spacing: Design.Theme.space2

            Label {
                Layout.alignment: Qt.AlignVCenter
                text: "建议"
                color: root.hasResult ? Design.Theme.accentHover : Design.Theme.textSecondary
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
                font.weight: Font.DemiBold
            }

            Item {
                Layout.fillWidth: true
            }

            Label {
                Layout.alignment: Qt.AlignVCenter
                text: root.stateText
                color: root.busy ? Design.Theme.accentHover : Design.Theme.textPlaceholder
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
            }

            Label {
                Layout.alignment: Qt.AlignVCenter
                visible: root.edited && !root.busy
                text: "还原"
                color: restoreArea.containsMouse ? Design.Theme.accentPressed
                                                 : Design.Theme.accent
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.captionFontSize
                font.underline: restoreArea.containsMouse

                MouseArea {
                    id: restoreArea

                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: suggestionArea.text = root.suggestionText
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.hasResult
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            TextArea {
                id: suggestionArea

                readOnly: root.busy
                leftPadding: Design.Theme.space4
                rightPadding: Design.Theme.space4
                topPadding: 0
                bottomPadding: Design.Theme.space4
                verticalAlignment: TextEdit.AlignTop
                background: null
                wrapMode: TextArea.Wrap
                selectByMouse: true
                opacity: root.busy ? 0.4 : 1
                color: Design.Theme.textPrimary
                selectionColor: Design.Theme.accent
                selectedTextColor: Design.Theme.textOnAccent
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize + 1

                Behavior on opacity {
                    NumberAnimation {
                        duration: 140
                        easing.type: Easing.OutCubic
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root.hasResult

            Label {
                anchors.centerIn: parent
                visible: !root.generating
                text: root.configured ? "生成后可直接修改，再采纳" : "未配置 AI 服务"
                color: root.configured ? Design.Theme.textPlaceholder : Design.Theme.warning
                font.family: Design.Theme.fontFamily
                font.pixelSize: Design.Theme.bodyFontSize
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: Design.Theme.space4
                anchors.rightMargin: Design.Theme.space4
                anchors.topMargin: Design.Theme.space1
                visible: root.generating
                spacing: Design.Theme.space3

                Repeater {
                    model: [1, 0.92, 0.55]

                    Rectangle {
                        id: skeletonBar

                        required property int index
                        required property real modelData

                        Layout.preferredWidth: parent.width * skeletonBar.modelData
                        Layout.preferredHeight: 12
                        radius: 6
                        color: Design.Theme.disabledSurface

                        SequentialAnimation on opacity {
                            running: root.generating && root.visible
                            loops: Animation.Infinite
                            PauseAnimation {
                                duration: skeletonBar.index * 160
                            }
                            NumberAnimation {
                                to: 0.35
                                duration: 620
                                easing.type: Easing.InOutSine
                            }
                            NumberAnimation {
                                to: 1
                                duration: 620
                                easing.type: Easing.InOutSine
                            }
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }

    Item {
        id: progressTrack

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 1
        height: 2
        visible: root.busy
        clip: true

        Rectangle {
            width: progressTrack.width * 0.3
            height: parent.height
            radius: 1
            color: Design.Theme.accent

            NumberAnimation on x {
                running: root.busy && root.visible
                loops: Animation.Infinite
                from: -progressTrack.width * 0.3
                to: progressTrack.width
                duration: 1100
                easing.type: Easing.InOutCubic
            }
        }
    }
}
