import QtQuick
import QtQuick.Controls

// 本项目的下拉菜单统一：点 opener 自身不触发关闭（默认策略会先关弹窗，使 toggle 读到的状态失真），
// 由 toggle() 负责开/合。
// 入场只做透明度渐变，覆盖样式自带的高度展开动画（后者逐帧改弹层 height，每帧都要重新布局并重切九宫格背景）。
// 用 OpacityAnimator 而非 NumberAnimation：动画在渲染线程执行，不与弹出的首帧争主线程。
// 不加退场动画：关闭即代表已选中，延迟消失只会显得迟钝；样式原本也只定义了 enter。
Menu {
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    enter: Transition {
        OpacityAnimator {
            from: 0
            to: 1
            duration: 90
        }
    }

    function toggle() {
        if (visible)
            close()
        else
            open()
    }
}
