/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.android.hiddevicesnippet;

import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import android.widget.Toast;

/** A simple Activity that exists solely to gain focus and capture key events. */
public class KeyCaptureActivity extends Activity {

    public static KeyCaptureActivity instance = null;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        instance = this;
        Toast.makeText(this, "KeyCaptureActivity Started.", Toast.LENGTH_LONG).show();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();

        if (instance == this) {
            instance = null;
        }
        Toast.makeText(this, "KeyCaptureActivity Stopped.", Toast.LENGTH_SHORT).show();
    }

    /**
     * Called when a key is pressed down.
     *
     * @param keyCode The physical key code.
     * @param event The full key event object.
     * @return boolean indicating if the event was consumed.
     */
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        // Log the key press to the static list in the Snippet class
        String keyName = KeyEvent.keyCodeToString(keyCode);
        synchronized (HIDDeviceSnippet.mKeyLog) {
            HIDDeviceSnippet.mKeyLog.add("DOWN: " + keyName);
        }

        // Log to Android logcat for debugging
        System.out.println("HIDDeviceSnippet: DOWN: " + keyName);

        // Return true to not propagate the key event to other Activities.
        return true;
    }

    /**
     * Called when a key is released.
     *
     * @param keyCode The physical key code.
     * @param event The full key event object.
     * @return boolean indicating if the event was consumed.
     */
    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event) {
        // Log the key release to the static list in the Snippet class
        String keyName = KeyEvent.keyCodeToString(keyCode);
        synchronized (HIDDeviceSnippet.mKeyLog) {
            HIDDeviceSnippet.mKeyLog.add("UP: " + keyName);
        }

        // Log to Android logcat for debugging
        System.out.println("HIDDeviceSnippet: UP: " + keyName);

        // Return true to not propagate the key event to other Activities.
        return true;
    }
}
