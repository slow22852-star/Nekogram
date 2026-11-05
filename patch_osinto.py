#!/usr/bin/env python3
import os
import re
import sys

# Корень репозитория (где запускается Action)
ROOT = os.getcwd()

MC = os.path.join(ROOT, "TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java")
PA = os.path.join(ROOT, "TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java")
ENGINE = os.path.join(ROOT, "TMessagesProj/src/main/java/org/telegram/messenger/OsintEngine.java")

def check_files():
    for f in [MC, PA]:
        if not os.path.exists(f):
            print(f"ОШИБКА: Файл не найден: {f}")
            sys.exit(1)

def patch_ghost():
    with open(MC, "r", encoding="utf-8") as f:
        src = f.read()

    if "GhostMode" in src:
        print("Ghost уже пропатчен")
        return

    ghost_class = """
class GhostMode {
    private static boolean enabled = false;
    public static void toggle() { enabled = !enabled; }
    public static boolean isEnabled() { return enabled; }
}
"""
    # Вставляем класс перед объявлением класса
    if "public class MessagesController" in src:
        src = src.replace("public class MessagesController", ghost_class + "\npublic class MessagesController", 1)
    else:
        print("ОШИБКА: Не найдено объявление public class MessagesController")
        sys.exit(1)

    # Патчим метод updateStatus
    # Ищем "public void updateStatus(boolean online) {"
    pattern = r"(public void updateStatus\(boolean online\)\s*\{)"
    replacement = r"\1\n        if (GhostMode.isEnabled()) online = false;"
    
    if re.search(pattern, src):
        src = re.sub(pattern, replacement, src, count=1)
    else:
        print("ПРЕДУПРЕЖДЕНИЕ: Метод updateStatus не найден. Возможно, в этой версии исходников он называется иначе.")

    with open(MC, "w", encoding="utf-8") as f:
        f.write(src)
    print("Ghost пропатчен")

def patch_osint_button():
    with open(PA, "r", encoding="utf-8") as f:
        src = f.read()

    if "Найти бича" in src:
        print("OSINT уже пропатчен")
        return

    marker = "public class ProfileActivity"
    inject = """
    private void addOsintMenuItem(android.view.Menu menu) {
        menu.add(0, 99999, 0, "Найти бича")
            .setOnMenuItemClickListener(item -> {
                if (getUserConfig().getCurrentUser() != null) {
                    final org.telegram.tgnet.TLRPC.User u = getUserConfig().getCurrentUser();
                    new Thread(() -> {
                        String report = OsintEngine.scan(u);
                        org.telegram.messenger.SendMessagesHelper.getInstance(currentAccount)
                            .sendMessage(report, new org.telegram.tgnet.TLRPC.TL_inputPeerSelf(),
                                null, null, null, true, 0);
                    }).start();
                }
                return true;
            });
    }
"""
    if marker in src:
        src = src.replace(marker, inject + "\n" + marker, 1)
    else:
        print("ОШИБКА: Не найден класс ProfileActivity")
        sys.exit(1)

    # ВАЖНО: Тут нужно вызвать addOsintMenuItem в методе создания меню.
    # В Nekogram это обычно метод onCreateOptionsMenu или createActionBarMenu.
    # Так как структура может меняться, мы внедряем вызов в onPrepareOptionsMenu, если он есть.
    if "public boolean onPrepareOptionsMenu(android.view.Menu menu)" in src:
        src = src.replace("public boolean onPrepareOptionsMenu(android.view.Menu menu) {", 
                          "public boolean onPrepareOptionsMenu(android.view.Menu menu) {\n        addOsintMenuItem(menu);")
    
    with open(PA, "w", encoding="utf-8") as f:
        f.write(src)
    print("OSINT кнопка пропатчена")

def patch_osint_engine():
    if os.path.exists(ENGINE):
        print("OsintEngine уже есть")
        return
    engine = r'''
package org.telegram.messenger;

import org.telegram.tgnet.TLRPC;
import java.net.*;
import java.util.regex.*;

public class OsintEngine {
    public static String scan(TLRPC.User user) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== ОТЧЁТ OSINTOgramm ===\n");
        sb.append("ID: ").append(user.id).append("\n");
        sb.append("Username: @").append(user.username == null ? "-" : user.username).append("\n");
        sb.append("Имя: ").append(user.first_name).append(" ").append(user.last_name).append("\n");
        sb.append("Bio: ").append(user.about == null ? "-" : user.about).append("\n\n");

        if (user.username != null && !user.username.isEmpty()) {
            sb.append("[Соцсети по username]\n");
            String[] sites = {"https://github.com/%s","https://instagram.com/%s","https://vk.com/%s","https://t.me/%s"};
            for (String s : sites) {
                String url = String.format(s, user.username);
                sb.append(url).append(" -> ").append(checkExists(url)).append("\n");
            }
        }

        String about = user.about == null ? "" : user.about;
        Matcher m = Pattern.compile("\\+?\\d[\\d\\s\\-()]{7,}").matcher(about);
        sb.append("\n[Номера из bio]\n");
        boolean found = false;
        while (m.find()) { sb.append(m.group()).append("\n"); found = true; }
        if (!found) sb.append("не найдено\n");

        sb.append("\n[Поиск по имени]\n");
        try {
            sb.append("https://duckduckgo.com/?q=").append(URLEncoder.encode(user.first_name + " " + user.last_name, "UTF-8")).append("\n");
        } catch (Exception e) {
            sb.append("https://duckduckgo.com\n");
        }

        return sb.toString();
    }

    private static String checkExists(String url) {
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
            c.setRequestMethod("HEAD");
            c.setConnectTimeout(5000);
            c.setInstanceFollowRedirects(true);
            int code = c.getResponseCode();
            return code == 200 ? "НАЙДЕН" : "нет";
        } catch (Exception e) { return "ошибка"; }
    }
}
'''
    with open(ENGINE, "w", encoding="utf-8") as f:
        f.write(engine)
    print("OsintEngine создан")

if __name__ == "__main__":
    check_files()
    patch_ghost()
    patch_osint_button()
    patch_osint_engine()
    print("Все патчи применены")