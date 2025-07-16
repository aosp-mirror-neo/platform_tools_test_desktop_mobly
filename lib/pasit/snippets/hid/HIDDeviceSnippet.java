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

import android.content.Context;
import android.hardware.input.InputManager;
import android.view.InputDevice;

import androidx.test.InstrumentationRegistry;

import com.google.android.mobly.snippet.Snippet;
import com.google.android.mobly.snippet.rpc.Rpc;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** A Mobly snippet that uses the Android Java APIs to interact with HID devices. */
public class HIDDeviceSnippet implements Snippet {

    private final Context mContext;
    private final InputManager mInputManager;

    public HIDDeviceSnippet() {
        mContext = InstrumentationRegistry.getTargetContext();
        mInputManager = mContext.getSystemService(InputManager.class);
    }

    /**
     * Gets a list of attached HID devices, filtered for keyboards and mice.
     *
     * @return A JSONArray of JSONObjects, each representing a device.
     * @throws JSONException if there is an error creating the JSON response.
     */
    @Rpc(description = "Gets a list of attached HID devices (keyboards and mice).")
    public JSONArray getHidDevices() throws JSONException {
        JSONArray devices = new JSONArray();
        int[] deviceIds = mInputManager.getInputDeviceIds();

        // Iterate over all attached input device IDs.
        for (int deviceId : deviceIds) {
            InputDevice dev = mInputManager.getInputDevice(deviceId);
            if (dev == null) {
                continue;
            }

            // Check the device's sources to determine if it's a keyboard or a mouse.
            boolean isKeyboard =
                    (dev.getSources() & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD;
            boolean isMouse =
                    (dev.getSources() & InputDevice.SOURCE_MOUSE) == InputDevice.SOURCE_MOUSE;

            // If the device is a keyboard or mouse, add it to our list.
            if (isKeyboard || isMouse) {
                JSONObject deviceInfo = new JSONObject();
                deviceInfo.put("name", dev.getName());
                deviceInfo.put("vendorId", dev.getVendorId());
                deviceInfo.put("productId", dev.getProductId());

                String type = "";
                if (isKeyboard) {
                    type += "Keyboard";
                }
                if (isMouse) {
                    type += (type.isEmpty() ? "Mouse" : " & Mouse");
                }
                deviceInfo.put("type", type);
                devices.put(deviceInfo);
            }
        }
        return devices;
    }

    @Override
    public void shutdown() {
        // Perform any necessary cleanup here.
    }
}
