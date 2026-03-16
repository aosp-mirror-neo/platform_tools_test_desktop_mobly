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

import android.os.Bundle;
import android.util.Log;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Toast;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;
import androidx.appcompat.app.AppCompatActivity;

/** A simple Activity that exists solely to gain focus and capture key and mouse events. */
public class CaptureActivity extends AppCompatActivity
    implements View.OnGenericMotionListener, OnBackInvokedCallback {

  /** Represents the types of key events we track. */
  public static enum KeyEventType {
    DOWN,
    UP
  }

  public static CaptureActivity instance = null;

  private static final String TAG = "HIDDeviceSnippet";

  // Store mouse position to avoid logging false move events when the actual cursor is not moving.
  private int mMouseX = 0;
  private int mMouseY = 0;

  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    instance = this;
    Toast.makeText(this, "CaptureActivity Started.", Toast.LENGTH_LONG).show();
    View contentView = findViewById(android.R.id.content);
    if (contentView == null) {
      Log.e(TAG, "Could not find android.R.id.content");
      return;
    }

    // to capture mouse events
    contentView.setOnGenericMotionListener(this);
    // to capture mouse back key events
    getOnBackInvokedDispatcher()
        .registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, this);
  }

  @Override
  public boolean onGenericMotion(View v, MotionEvent event) {
    Log.d(TAG, "onGenericMotion: " + event.toString());

    if (!event.isFromSource(InputDevice.SOURCE_MOUSE)) {
      return false; // Event not consumed
    }

    switch (event.getAction()) {
      case MotionEvent.ACTION_HOVER_MOVE -> {
        // Ignore ACTION_HOVER_MOVE events if the cursor position hasn't changed.
        // This prevents logging a move event when the user is only scrolling.
        if (Math.abs(event.getX() - mMouseX) < 1 && Math.abs(event.getY() - mMouseY) < 1) {
          Log.d(TAG, "onGenericMotion: Mouse cursor is not moving.");
          return false; // Event not consumed
        }
        mMouseX = (int) event.getX();
        mMouseY = (int) event.getY();
        logMouseEvent(MotionEvent.actionToString(event.getAction()));
      }
      case MotionEvent.ACTION_SCROLL ->
          logMouseEvent(MotionEvent.actionToString(event.getAction()));
      case MotionEvent.ACTION_BUTTON_PRESS ->
          logMouseEvent(KeyEventType.DOWN, getButtonName(event.getButtonState()));
      case MotionEvent.ACTION_BUTTON_RELEASE ->
          logMouseEvent(KeyEventType.UP, getButtonName(event.getButtonState()));
    }
    return true; // Event consumed
  }

  @Override
  public void onBackInvoked() {
    // KEYCODE_BACK is a fundamental navigation key in Android. The system (Activity Manager, Window
    // Manager) almost always intercepts and consumes this key event to trigger the default "back"
    // action (e.g., close the current activity, go back in the navigation stack).
    // By registering an OnBackInvokedCallback, we can detect when the system's "back" action is
    // triggered, which will include presses of the mouse button mapped to BTN_SIDE.
    logMouseEvent(KeyEventType.DOWN, "BACK");
    logMouseEvent(KeyEventType.UP, "BACK");
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

    String keyName = KeyEvent.keyCodeToString(event.getKeyCode());
    switch (event.getSource()) {
      case InputDevice.SOURCE_MOUSE -> logMouseEvent(KeyEventType.DOWN, keyName);
      case InputDevice.SOURCE_KEYBOARD -> logKeyEvent(KeyEventType.DOWN, keyName);
    }

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

    String keyName = KeyEvent.keyCodeToString(event.getKeyCode());
    switch (event.getSource()) {
      case InputDevice.SOURCE_MOUSE -> logMouseEvent(KeyEventType.UP, keyName);
      case InputDevice.SOURCE_KEYBOARD -> logKeyEvent(KeyEventType.UP, keyName);
    }

    // Return true to not propagate the key event to other Activities.
    return true;
  }

  private static void logKeyEvent(KeyEventType action, String keyName) {
    synchronized (HIDDeviceSnippet.mKeyLog) {
      HIDDeviceSnippet.mKeyLog.add(action.name() + ": " + keyName);
    }
  }

  private static void logMouseEvent(KeyEventType action, String button) {
    synchronized (HIDDeviceSnippet.mMouseLog) {
      HIDDeviceSnippet.mMouseLog.add(action.name() + ": " + button);
    }
  }

  private static void logMouseEvent(String event) {
    synchronized (HIDDeviceSnippet.mMouseLog) {
      HIDDeviceSnippet.mMouseLog.add(event);
    }
  }

  private static String getButtonName(int button) {
    return switch (button) {
      case MotionEvent.BUTTON_PRIMARY -> "PRIMARY";
      case MotionEvent.BUTTON_SECONDARY -> "SECONDARY";
      case MotionEvent.BUTTON_TERTIARY -> "TERTIARY";
      case MotionEvent.BUTTON_BACK -> "BACK";
      case MotionEvent.BUTTON_FORWARD -> "FORWARD";
      default -> "UNKNOWN";
    };
  }
}
