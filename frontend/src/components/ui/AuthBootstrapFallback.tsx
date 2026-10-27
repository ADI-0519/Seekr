import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

export function AuthBootstrapFallback() {
    return (
        <View style={styles.container} testID="auth-bootstrap-loading">
            <ActivityIndicator size="small" />
            <Text style={styles.label}>Loading session...</Text>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
    },
    label: {
        fontSize: 14,
    },
});
