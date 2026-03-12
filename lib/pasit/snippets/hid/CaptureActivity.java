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
import android.util.Log;
import android.view.KeyEvent;
import android.widget.Toast;

/** A simple Activity that exists solely to gain focus and capture key events. */
public class CaptureActivity extends Activity {

  /** Represents the types of key events we track. */
  public static enum KeyEventType {
    DOWN,
    UP
  }

  public static CaptureActivity instance = null;

  private static final String TAG = "HIDDeviceSnippet";

  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    instance = this;
    Toast.makeText(this, "CaptureActivity Started.", Toast.LENGTH_LONG).show();
  }

  @Override
  public void onDestroy() {
    super.onDestroy();

    if (instance == this) {
      instance = null;
    }
    Toast.makeText(this, "CaptureActivity Stopped.", Toast.LENGTH_SHORT).show();
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
    Log.d(TAG, "onKeyDown: " + event.toString());
    logKeyEvent(KeyEventType.DOWN, event.getKeyCode());
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
    Log.d(TAG, "onKeyUp: " + event.toString());
    logKeyEvent(KeyEventType.UP, event.getKeyCode());
    // Return true to not propagate the key event to other Activities.
    return true;
  }

  private static void logKeyEvent(KeyEventType action, int keyCode) {
    synchronized (HIDDeviceSnippet.mKeyLog) {
      HIDDeviceSnippet.mKeyLog.add(action.name() + ": " + KeyEvent.keyCodeToString(keyCode));
    }
  }
}
